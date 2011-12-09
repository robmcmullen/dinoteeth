#!/usr/bin/env python
# -*- coding: utf-8 -*-

from dinoteeth_test import *

from mplayer import *

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
        self.assertEqual(m.audio[0].id, 0)
        self.assertEqual(m.audio[0].name, "Audio Track #1")
        self.assertEqual(m.audio[0].lang, "eng")
        self.assertEqual(m.ID_AID_1_NAME, "Audio Track #2")
        self.assertEqual(m.audio[1].id, 1)
        self.assertEqual(m.audio[1].name, "Audio Track #2")
        self.assertEqual(m.audio[1].lang, "epo")
        
    def testSubtitles(self):
        m = MPlayerInfo("test-100_frames-2_audio_tracks.mkv")
        self.assertEqual(m.ID_FILENAME, "test-100_frames-2_audio_tracks.mkv")
        self.assertEqual(m.ID_LENGTH, "10.06")
        self.assertEqual(m.ID_SID_0_NAME, "Subtitle #1")
        self.assertEqual(m.subtitles[0].id, 0)
        self.assertEqual(m.subtitles[0].name, "Subtitle #1")
        self.assertEqual(m.subtitles[0].lang, "eng")
        self.assertEqual(m.ID_SID_1_NAME, "Subtitle #2")
        self.assertEqual(m.subtitles[1].id, 1)
        self.assertEqual(m.subtitles[1].name, "Subtitle #2")
        self.assertEqual(m.subtitles[1].lang, "epo")


if __name__ == '__main__':
    test_all()
