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

from dinoteeth_test import *

from dinoteeth.media import guess_custom
from dinoteeth.config import Config
from dinoteeth.database import DictDatabase

class TestDatabaseGeneral(TestCase):
    def setUp(self):
        self.config = Config([])
        self.db = DictDatabase()
        
    def testFind(self):
        results = self.db.find("photos")
        assert len(results) == 0
        h = results.hierarchy()
        self.assertEqual(len(h.children), 0)
    

class TestDatabaseHierarchyMovies1(TestCase):
    def setUp(self):
        self.config = Config([])
        self.db = DictDatabase()
        self.config.parse_dir(self.db, "movies1")
        
    def testFind(self):
        results = self.db.find("movie")
        assert len(results) == 38
        h = results.hierarchy()
        self.assertEqual(len(h.children), 15)
    
    def testFindChildren1(self):
        results = self.db.find("movie", lambda s:s['title'] == "Moon")
        h = results.hierarchy()
        self.assertEqual(len(h.children), 1)
        self.assertEqual(len(h.children[0].children), 5)
        self.assertEqual(h.children[0].children[0]['title'], "Moon")
        self.assertEqual(h.children[0].children[0]['extraNumber'], 1)
    
    def testFindChildren2(self):
        results = self.db.find("movie", lambda s:s['title'] == "The Hunt for Red October")
        h = results.hierarchy()
        self.assertEqual(len(h.children), 1)
        self.assertEqual(len(h.children[0].children), 2)
        self.assertEqual(h.children[0].children[0]['title'], "The Hunt for Red October")
        self.assert_('extraNumber' not in h.children[0].children[0])
        self.assertEqual(h.children[0].children[1]['title'], "The Hunt for Red October")
        self.assertEqual(h.children[0].children[1]['extraNumber'], 1)
        
class TestDatabaseHierarchySeries1(TestCase):
    def setUp(self):
        self.config = Config([])
        self.db = DictDatabase()
        self.config.parse_dir(self.db, "series1")
        
    def testFind(self):
        results = self.db.find("episode")
        self.assertEqual(len(results), 32)
        h = results.hierarchy()
        print h
        self.assertEqual(len(h.children), 5)
    
    def testFindChildren1(self):
        results = self.db.find("episode", lambda s:s['series'] == "The Big Bang Theory")
        self.assertEqual(len(results), 22)
        h = results.hierarchy()
        print h
        self.assertEqual(len(h.children), 1)
        
        # Look at the series
        series = h.children[0]
        self.assertEqual(series['series'], "The Big Bang Theory")
        
        # Look at the second season
        season2 = series.children[1]
        self.assertEqual(season2['series'], "The Big Bang Theory")
        c = season2.children
        self.assertEqual(len(c), 6)
        self.assertEqual(c[0]['series'], "The Big Bang Theory")
        self.assertEqual(c[0]['season'], 2)
        self.assertEqual(c[0]['episodeNumber'], 1)
        self.assertEqual(c[1]['series'], "The Big Bang Theory")
        self.assertEqual(c[1]['season'], 2)
        self.assertEqual(c[1]['episodeNumber'], 2)
        self.assertEqual(c[5]['series'], "The Big Bang Theory")
        self.assertEqual(c[5]['season'], 2)
        self.assertEqual(c[5]['extraNumber'], 3)


if __name__ == '__main__':
    test_all()
