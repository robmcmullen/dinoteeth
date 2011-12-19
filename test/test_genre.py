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

from media import guess_custom
from config import Config
from database import DictDatabase

class TestDatabaseGenre1(TestCase):
    def setUp(self):
        self.config = Config([])
        self.db = DictDatabase()
        self.db.loadStateFromFile("movies1/dinoteeth.db")
        
    def testFind(self):
        results = self.db.find("movie")
        assert len(results) == 38
    
    def testFindOne(self):
        results = self.db.find("movie", lambda s:s.has_metadata('genres', 'Comedy'))
        self.assertEquals(len(results), 6)
        results = self.db.find("movie", lambda s:s.has_metadata('genres', 'Adventure'))
        self.assertEquals(len(results), 8)
        results = self.db.find("movie", lambda s:s.has_metadata('genres', 'Biography'))
        self.assertEquals(len(results), 1)
    
    def testFindAllGenres(self):
        results = self.db.find("movie")
        genres = results.all_metadata('genres')
        self.assertEquals(len(genres), 13)
    
    def testFindAllDirectors(self):
        results = self.db.find("movie")
        people = results.all_metadata('directors')
        self.assertEquals(len(people), 12)
        results = self.db.find("movie", lambda s:s.has_metadata('directors', 'Edgar Wright'))
        self.assertEquals(len(results), 1)
        self.assertEquals(results[0]['title'], "Shaun of the Dead")
        


if __name__ == '__main__':
    test_all()
