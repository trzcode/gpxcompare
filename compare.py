import geo
import gpxpy
import logging
import math
import numpy

_log = logging.getLogger(__name__)

def align_tracks(track1, track2, gap_penalty):
    """ Needleman-Wunsch algorithm adapted for gps tracks. """

    _log.info("Aligning tracks")

    def similarity(p1, p2):
        d = gpxpy.geo.distance(p1.latitude, p1.longitude, p1.elevation,
                               p2.latitude, p2.longitude, p2.elevation)
        return -d

    # construct f-matrix
    f = numpy.zeros((len(track1), len(track2)))
    for i in range(0, len(track1)):
        f[i][0] = gap_penalty * i
    for j in range(0, len(track2)):
        f[0][j] = gap_penalty * j
    for i in range(1, len(track1)):
        t1 = track1[i]
        for j in range(1, len(track2)):
            t2 = track2[j]
            match = f[i-1][j-1] + similarity(t1, t2)
            delete = f[i-1][j] + gap_penalty
            insert = f[i][j-1] + gap_penalty
            f[i, j] = max(match, max(delete, insert))

    # backtrack to create alignment
    a1 = []
    a2 = []
    i = len(track1) - 1
    j = len(track2) - 1
    while i > 0 or j > 0:
        if i > 0 and j > 0 and \
           f[i, j] == f[i-1][j-1] + similarity(track1[i], track2[j]):
            a1.insert(0, track1[i])
            a2.insert(0, track2[j])
            i -= 1
            j -= 1
        elif i > 0 and f[i][j] == f[i-1][j] + gap_penalty:
            a1.insert(0, track1[i])
            a2.insert(0, None)
            i -= 1
        elif j > 0 and f[i][j] == f[i][j-1] + gap_penalty:
            a1.insert(0, None)
            a2.insert(0, track2[j])
            j -= 1
    return a1, a2

def isReverted(track1, track2, num_points):
    """ Tests whether two tracks are likely to be a reversal of each other or not """
    # Ensure num_points is no greater than the length of either track
    num_points = min(num_points, len(track1), len(track2))

    def displacement(track1, track2, index1, index2):
        """ Returns distance between track1[index1] and track2[index2] """
        return gpxpy.geo.distance(track1[index1].latitude, track1[index1].longitude, None, track2[index2].latitude, track2[index2].longitude, None)

    sum_displacement_regular = 0
    sum_displacement_opposite = 0

    for i in range(num_points):
        sum_displacement_regular += displacement(track1, track2, i, i)
        sum_displacement_opposite += displacement(track1, track2, i, -i)

        return sum_displacement_regular <= sum_displacement_opposite

def calculateSimilarity(gpx1, gpx2, gapPenalty, ignoreElevation, even):
    # Join all the points from all segments for the track into a single list
    gpx1_points = [p for s in gpx1.tracks[0].segments for p in s.points]
    gpx2_points = [p for s in gpx2.tracks[0].segments for p in s.points]
    
    if isReverted(gpx1_points, gpx2_points, 40):
        _log.info("Detected a track that needs to be reversed")
        gpx1_points.reverse()
    
    # Evenly distribute the points
    if even:
        gpx1_points = geo.interpolate_distance(gpx1_points, even)
        gpx2_points = geo.interpolate_distance(gpx2_points, even)
    
    # Run the alignment
    a1, a2 = align_tracks(gpx1_points, gpx2_points, gapPenalty)

    # Output the difference in the tracks as a percentage
    match = 0
    for i in range(0, len(a1)):
        if a1[i] is not None and a2[i] is not None:
            match += 1
    total_similar = match / len(a1)

    return total_similar, a1, a2