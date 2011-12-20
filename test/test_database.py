#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# GuessIt - A library for guessing information from filenames
# Copyright (c) 2011 Nicolas Wack <wackou@gmail.com>
#
# GuessIt is free software; you can redistribute it and/or modify it under
# the terms of the Lesser GNU General Public License as published by
# the Free Software Foundation; either version 3 of the License, or
# (at your option) any later version.
#
# GuessIt is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# Lesser GNU General Public License for more details.
#
# You should have received a copy of the Lesser GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#

import unittest
from guessittest import *

from media import guess_custom
from config import Config
from database import DictDatabase

class TestDatabaseMovies1(TestCase):
    def setUp(self):
        self.config = Config([])
        self.db = DictDatabase()
        self.config.parse_dir(self.db, "movies1")
        
    def testFind(self):
        results = self.db.find("movie")
        assert len(results) == 38
    
    def testFindOne(self):
        results = self.db.find("movie", lambda s:s['title'] == "Toy Story")
        assert len(results) == 1
    
    def testFindSeries1(self):
        results = self.db.find("movie", lambda s:s['title'] == "Moon")
        assert len(results) == 5
    
    def testFindSeries2(self):
        results = self.db.find("movie", lambda s:s['title'] == "The Social Network")
        assert len(results) == 7
    
    def testFindMain1(self):
        results = self.db.find("movie", lambda s:s['title'] == "Moon" and 'extraNumber' not in s)
        assert len(results) == 0
    
    def testFindMain2(self):
        results = self.db.find("movie", lambda s:s['title'] == "The Social Network" and 'extraNumber' not in s)
        assert len(results) == 1
    
    def testSort1(self):
        results = self.db.find("movie")
        assert len(results) == 38
        self.assertEqual(results[0]['title'], "Battle Los Angeles")
        self.assertEqual(results[1]['title'], "Death at a Funeral")
        self.assertEqual(results[22]['title'], "Shaun of the Dead")
        self.assertEqual(results[-1]['title'], "Toy Story 3")
    
    def testFindFranchise1(self):
        results = self.db.find("movie", lambda s:s.get('franchise') == "Toy Story")
        assert len(results) == 3
        self.assertEqual(results[0]['title'], "Toy Story")
        self.assertEqual(results[1]['title'], "Toy Story 2")
        self.assertEqual(results[2]['title'], "Toy Story 3")


class TestDatabaseSeries1(TestCase):
    def setUp(self):
        self.config = Config([])
        self.db = DictDatabase()
        self.config.parse_dir(self.db, "series1")
        
    def testFind(self):
        results = self.db.find("episode")
        self.assertEqual(len(results), 32)
    
    def testFindOne(self):
        results = self.db.find("movie", lambda s:s['series'] == "The Wire")
        self.assertEqual(len(results), 0)
        results = self.db.find("episode", lambda s:s['series'] == "The Wire")
        self.assertEqual(len(results), 3)
    
    def testFindExtra(self):
        results = self.db.find("episode", lambda s:s['series'] == "The Big Bang Theory" and s['season'] == 1)
        self.assertEqual(len(results), 4)
        self.assertEqual(results[0]['season'], 1)
        self.assertEqual(results[0]['episodeNumber'], 1)
        self.assertEqual(results[1]['season'], 1)
        self.assertEqual(results[1]['episodeNumber'], 2)
        self.assertEqual(results[2]['season'], 1)
        self.assertEqual(results[2]['episodeNumber'], 3)
        self.assertEqual(results[3]['season'], 1)
        self.assertEqual(results[3]['extraNumber'], 1)
        results = self.db.find("episode", lambda s:s['series'] == "The Big Bang Theory" and s['season'] == 1 and 'extraNumber' not in s)
        self.assertEqual(len(results), 3)
        results = self.db.find("episode", lambda s:s['series'] == "The Big Bang Theory" and s['season'] == 1 and 'extraNumber' in s)
        self.assertEqual(len(results), 1)
        results = self.db.find("episode", lambda s:s['series'] == "The Big Bang Theory" and s['season'] == 2)
        self.assertEqual(len(results), 6)
        self.assertEqual(results[0]['season'], 2)
        self.assertEqual(results[0]['episodeNumber'], 1)
        self.assertEqual(results[5]['season'], 2)
        self.assertEqual(results[5]['extraNumber'], 3)


if __name__ == '__main__':
    for case in [TestDatabaseMovies1, TestDatabaseSeries1]:
        suite = unittest.TestLoader().loadTestsFromTestCase(case)
        TextTestRunner(verbosity=2).run(suite)
