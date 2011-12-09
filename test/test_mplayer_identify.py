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


if __name__ == '__main__':
    test_all()
