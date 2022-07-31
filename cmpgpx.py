#!/usr/bin/env python3

import argparse
import logging
import math
import os

logging.basicConfig(
    format='%(asctime)s | %(levelname)s | %(message)s', level=logging.INFO)
_log = logging.getLogger(__name__)
logging.getLogger('geotiler').setLevel(logging.INFO)
logging.getLogger('geotiler.map').setLevel(logging.INFO)
logging.getLogger('geotiler.tilenet').setLevel(logging.INFO)

import cairocffi as cairo
import geotiler
import gpxpy
import numpy

import compare
import gfx

def draw_alignment(track1, track2, bounds):
    """ Draws the aligned tracks with the given bounds onto a cairo surface. """

    _log.info("Drawing alignment")

    mm = geotiler.Map(extent=bounds, zoom=14)
    width, height = mm.size
    image = geotiler.render_map(mm)

    # create cairo surface
    buff = bytearray(image.convert('RGBA').tobytes('raw', 'BGRA'))
    surface = cairo.ImageSurface.create_for_data(
        buff, cairo.FORMAT_ARGB32, width, height)
    cr = cairo.Context(surface)

    a1_l = len(track1)
    a2_l = len(track2)
    assert a1_l == a2_l
    p_radius = 2
    for i in range(0, a1_l):
        if track1[i] is not None and track2[i] is not None:
            cr.set_source_rgba(0.2, 0.7, 1.0, 1.0)
            a1_x, a1_y = mm.rev_geocode((track1[i].longitude, track1[i].latitude))
            cr.arc(a1_x, a1_y, p_radius, 0, 2 * math.pi)
            cr.fill()
            cr.set_source_rgba(0.0, 0.0, 1.0, 1.0)
            a2_x, a2_y = mm.rev_geocode((track2[i].longitude, track2[i].latitude))
            cr.arc(a2_x, a2_y, p_radius, 0, 2 * math.pi)
            cr.fill()
        elif track1[i] is not None and track2[i] is None:
            cr.set_source_rgba(1.0, 0.0, 0.0, 1.0)
            a1_x, a1_y = mm.rev_geocode((track1[i].longitude, track1[i].latitude))
            cr.arc(a1_x, a1_y, p_radius, 0, 2 * math.pi)
            cr.fill()
        elif track1[i] is None and track2[i] is not None:
            cr.set_source_rgba(1.0, 0.5, 0.0, 1.0)
            a2_x, a2_y = mm.rev_geocode((track2[i].longitude, track2[i].latitude))
            cr.arc(a2_x, a2_y, p_radius, 0, 2 * math.pi)
            cr.fill()
    return surface


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('gpx_file1', type=argparse.FileType('r'))
    parser.add_argument('gpx_file2', type=argparse.FileType('r'))
    parser.add_argument('-c', '--cutoff', type=int, default=10,
                        help="cutoff distance in meters for similar points")
    parser.add_argument('-d', '--debug', action='store_true')
    parser.add_argument('-e', '--even', type=int,
                        help="evenly distribute points in meters")
    parser.add_argument('-o', '--output-file', default="alignment.png",
                        help="output filename")
    parser.add_argument('-s', '--separate_tracks', action='store_true',
                        help="output original tracks to separate images")
    parser.add_argument('-i', '--ignore-elevation', action='store_true')
    args = parser.parse_args()

    if args.debug:
        _log.setLevel(logging.DEBUG)
        logging.getLogger('geotiler.tilenet').setLevel(logging.DEBUG)

    ignoreElevation = True if args.ignore_elevation else False

    gap_penalty = -args.cutoff

    gpxComparator = compare.GpxComparator(gap_penalty, args.even, ignoreElevation)
    gpxComparator.loadTracksFromFiles(args.gpx_file1, args.gpx_file2)
    gpxComparator.calculateSimilarity()

    # Calculate map bounding box with padding
    padding_pct = 10
    bounds1 = gpxComparator.originalTrack1.get_bounds()
    bounds2 = gpxComparator.originalTrack2.get_bounds()
    bbox1 = gfx.add_padding((bounds1.min_longitude, bounds1.min_latitude,
                             bounds1.max_longitude, bounds1.max_latitude), 10)
    bbox2 = gfx.add_padding((bounds2.min_longitude, bounds2.min_latitude,
                             bounds2.max_longitude, bounds2.max_latitude), 10)
    bbox = (min(bbox1[0], bbox2[0]), min(bbox1[1], bbox2[1]),
            max(bbox1[2], bbox2[2]), max(bbox1[3], bbox2[3]))

    # Draw tracks and alignment
    if args.separate_tracks:
        gpx1_surface = gfx.draw_track(gpxComparator.distributedTrack1Points, bbox1)
        gpx1_img_filename = "{}.png".format(
            os.path.basename(os.path.splitext(args.gpx_file1.name)[0]))
        _log.info("Saving original track to '{}'".format(gpx1_img_filename))
        gpx1_surface.write_to_png(gpx1_img_filename)

        gpx2_surface = gfx.draw_track(gpxComparator.distributedTrack2Points, bbox2)
        gpx2_img_filename = "{}.png".format(
            os.path.basename(os.path.splitext(args.gpx_file2.name)[0]))
        _log.info("Saving original track to '{}'".format(gpx2_img_filename))
        gpx2_surface.write_to_png(gpx2_img_filename)

    surface = draw_alignment(gpxComparator.alignedTrack1, gpxComparator.alignedTrack2, bbox)
    _log.info("Saving alignment to '{}'".format(args.output_file))
    surface.write_to_png(args.output_file)

    _log.info("Track Similarity: {:.2%}".format(gpxComparator.similarity))
