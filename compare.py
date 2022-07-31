import geo
import gpxpy
import logging
import math
import numpy

_log = logging.getLogger(__name__)

class GpxComparator:
    originalTrack1 = None
    originalTrack2 = None
    distributedTrack1Points = None
    distributedTrack2Points = None
    alignedTrack1 = None
    alignedTrack2 = None
    similarity = 0

    def __init__(self, gapPenalty, even, ignoreElevation):
        self.gapPenalty = gapPenalty
        self.even = even
        self.ignoreElevation = ignoreElevation
    
    def loadTrack1FromFile(self, trackFilename):
        self.originalTrack1 = gpxpy.parse(trackFilename)
    
    def loadTrack2FromFile(self, trackFilename):
        self.originalTrack2 = gpxpy.parse(trackFilename)
    
    def loadTracksFromFiles(self, track1Filename, track2Filename):
        self.loadTrack1FromFile(track1Filename)
        self.loadTrack2FromFile(track2Filename)
    
    def align(self):
        """ Needleman-Wunsch algorithm adapted for gps tracks. """

        _log.info("Aligning tracks")

        def similarity(p1, p2):
            elevation1 = p1.elevation if not self.ignoreElevation else None
            elevation2 = p2.elevation if not self.ignoreElevation else None
            d = gpxpy.geo.distance(p1.latitude, p1.longitude, elevation1,
                                   p2.latitude, p2.longitude, elevation2) 
            return -d

        track1 = self.distributedTrack1Points
        track2 = self.distributedTrack2Points

        # construct f-matrix
        f = numpy.zeros((len(track1), len(track2)))
        for i in range(0, len(track1)):
            f[i][0] = self.gapPenalty * i
        for j in range(0, len(track2)):
            f[0][j] = self.gapPenalty * j
        for i in range(1, len(track1)):
            t1 = track1[i]
            for j in range(1, len(track2)):
                t2 = track2[j]
                match = f[i-1][j-1] + similarity(t1, t2)
                delete = f[i-1][j] + self.gapPenalty
                insert = f[i][j-1] + self.gapPenalty
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
            elif i > 0 and f[i][j] == f[i-1][j] + self.gapPenalty:
                a1.insert(0, track1[i])
                a2.insert(0, None)
                i -= 1
            elif j > 0 and f[i][j] == f[i][j-1] + self.gapPenalty:
                a1.insert(0, None)
                a2.insert(0, track2[j])
                j -= 1
        self.alignedTrack1 = a1
        self.alignedTrack2 = a2

    def calculateSimilarity(self):
        # Join all the points from all segments for the track into a single list
        self.distributedTrack1Points = [p for s in self.originalTrack1.tracks[0].segments for p in s.points]
        self.distributedTrack2Points = [p for s in self.originalTrack2.tracks[0].segments for p in s.points]
        
        if geo.isTrackReverted(self.distributedTrack1Points, self.distributedTrack2Points, 40):
            _log.info("Detected a track that needs to be reversed")
            self.distributedTrack1Points.reverse()
        
        # Evenly distribute the points
        if self.even:
            self.distributedTrack1Points = geo.interpolate_distance(self.distributedTrack1Points, self.even)
            self.distributedTrack2Points = geo.interpolate_distance(self.distributedTrack2Points, self.even)
        
        # Run the alignment
        self.align()

        # Output the difference in the tracks as a percentage
        match = 0
        for i in range(0, len(self.alignedTrack1)):
            if self.alignedTrack1[i] is not None and self.alignedTrack2[i] is not None:
                match += 1
        
        self.similarity = match / len(self.alignedTrack1)