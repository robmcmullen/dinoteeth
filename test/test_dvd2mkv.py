#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os, sys

from dinoteeth_test import *

sys.path.insert(0, "../bin") # to find dvd2mkv.py
from dvd2mkv import *

class TestHandBrakeScan(TestCase):
    def setUp(self):
        pass
        
    def testMultiTitleScan(self):
        stderr = open("handbrake/DVDVIDEO1.txt").read()
        h = HandBrakeScanner("", test_stderr=stderr)
        self.assertEqual(h.num_titles, 32)
        self.assertEqual(len(h.titles), 32)
        self.assertEqual(len(h.titles[0].audio), 1)
        audio = h.titles[0].audio[0]
        self.assertEqual(audio.id, 128)
        self.assertEqual(audio.threecc, "eng")
        
    def testMultiAudioScan(self):
        stderr = open("handbrake/CASTAWAY_DTS.txt").read()
        h = HandBrakeScanner("", test_stderr=stderr)
        self.assertEqual(h.num_titles, 10)
        title = h.titles[0]
        self.assert_(title.main_feature)
        self.assertEqual(title.vts, 3)
        self.assertEqual(title.size, "720x480")
        self.assertEqual(title.pixel_aspect, "32/27")
        self.assertEqual(title.display_aspect, "1.78")
        self.assertEqual(len(title.audio), 5)
        audio = title.audio[0]
        self.assertEqual(audio.id, 136)
        self.assertEqual(audio.threecc, "eng")
        self.assert_("DTS" in audio.codec)
        self.assert_("5.1 ch" in audio.codec)
        audio = h.titles[0].audio[1]
        self.assertEqual(audio.id, 129)
        self.assertEqual(audio.threecc, "eng")
        self.assert_("AC3" in audio.codec)
        self.assert_("5.1 ch" in audio.codec)
        audio = h.titles[0].audio[2]
        self.assertEqual(audio.id, 130)
        self.assertEqual(audio.threecc, "eng")
        self.assert_("AC3" in audio.codec)
        self.assert_("Dolby Surround" in audio.codec)
        audio = h.titles[0].audio[3]
        self.assertEqual(audio.id, 131)
        self.assertEqual(audio.threecc, "fra")
        audio = h.titles[0].audio[4]
        self.assertEqual(audio.id, 132)
        self.assertEqual(audio.threecc, "eng")
        
        title = h.titles[2]
        self.assert_(not title.main_feature)
        self.assertEqual(title.vts, 7)
        self.assertEqual(title.size, "720x480")
        self.assertEqual(title.pixel_aspect, "8/9")
        self.assertEqual(title.display_aspect, "1.33")


if __name__ == '__main__':
    test_all()
