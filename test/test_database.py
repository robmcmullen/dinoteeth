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

from guessittest import *

from media import guess_custom
from config import Config, RootMenu
from database import DictDatabase

class TestDatabaseMovies1(TestCase):
    def setUp(self):
        self.config = Config([])
        self.db = DictDatabase()
        self.root = RootMenu(self.db)
        self.config.parse_dir(self.root, "movies1")
        
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
        print "\n".join("%s %s %s" % (r['title'], r.get('extraNumber', ''), r.get('extraTitle', '')) for r in results)
        self.assertEqual(results[0]['title'], "Battle Los Angeles")
        self.assertEqual(results[1]['title'], "Death at a Funeral")
        self.assertEqual(results[22]['title'], "Shaun of the Dead")
        self.assertEqual(results[-1]['title'], "Toy Story 3")


suite = allTests(TestDatabaseMovies1)

if __name__ == '__main__':
    TextTestRunner(verbosity=2).run(suite)
