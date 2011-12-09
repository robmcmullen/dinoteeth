#!/usr/bin/env python
# -*- coding: utf-8 -*-

from dinoteeth_test import *

from mplayerlib import *

class TestMPlayerIdentify(TestCase):
    def setUp(self):
        pass
        
    def testVideoOnly(self):
        m = MPlayerInfo("test200.mp4")
        self.assertEqual(m.ID_FILENAME, "test200.mp4")
        self.assertEqual(m.ID_LENGTH, "40.00")
        
    def testAudio(self):
        m = MPlayerInfo("test-100_frames-2_audio_tracks.mkv")
        self.assertEqual(m.ID_FILENAME, "test-100_frames-2_audio_tracks.mkv")
        self.assertEqual(m.ID_LENGTH, "10.06")
        self.assertEqual(m.ID_AID_0_NAME, "Audio Track #1")
        self.assertEqual(m.ID_AID_1_NAME, "Audio Track #2")


if __name__ == '__main__':
    test_all()
