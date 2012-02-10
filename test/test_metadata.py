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

from dinoteeth.metadata2 import BaseMetadata, MovieMetadata, MovieMetadataDatabase

class IMDbObject(dict):
    count = 1
    @classmethod
    def get_id(cls):
        cls.count += 1
        return str(cls.count)
    
    def __init__(self):
        dict.__init__(self)
        self.movieID = self.get_id()
        self.personID = self.get_id()
        self['canonical name'] = "Last, First"
        self.notes = ""

class TestBaseMetadata(TestCase):
    def setUp(self):
        self.db = MovieMetadataDatabase()
        self.imdb_obj = IMDbObject()
        self.imdb_obj['certificates'] = [u'Iceland:L', u'Portugal:M/12', u'Finland:S', u'Germany:6', u'Netherlands:AL', u'Spain:T', u'Sweden:7', u'UK:15', u'USA:PG-13', u'Canada:14::(Nova Scotia)', u'Australia:M']
        self.imdb_obj['runtimes'] = [u'95']
    
    def testCountryList(self):
        b = BaseMetadata()
        cert = b.get_country_list(self.imdb_obj, 'certificates', "USA")
        self.assertEqual(cert, "PG-13")
        cert = b.get_country_list(self.imdb_obj, 'certificates', "UK")
        self.assertEqual(cert, "15")
        cert = b.get_country_list(self.imdb_obj, 'certificates', "Australia")
        self.assertEqual(cert, "M")
        runtime = b.get_country_list(self.imdb_obj, 'runtimes', "USA")
        self.assertEqual(runtime, u"95")
    
    def testPrunePeople(self):
        producers = [IMDbObject() for i in range(6)]
        producers[0].notes = "producer"
        producers[0]['canonical name'] = u"Jones, Terry"
        producers[1].notes = "executive producer"
        producers[1]['canonical name'] = u"Gilliam, Terry"
        producers[2].notes = "executive producer"
        producers[2]['canonical name'] = u"Cleese, John"
        producers[3].notes = "associate producer"
        producers[3]['canonical name'] = u"Idle, Eric"
        producers[4].notes = "associate producer"
        producers[4]['canonical name'] = u"Palin, Michael"
        producers[5].notes = "producer"
        producers[5]['canonical name'] = u"Rabbit"
        b = BaseMetadata()
        executive_producers = self.db.prune_people(producers, 'executive producer')
        self.assertEqual(len(executive_producers), 2)
        producers = self.db.prune_people(producers)
        self.assertEqual(len(producers), 4)
        print self.db


class TestMovieMetadata(TestCase):
    def setUp(self):
        self.db = MovieMetadataDatabase()
        
    def test1(self):
        movie = self.db.fetch_movie("0102250")
        print movie
        self.assertEqual(movie.title, "L.A. Story")
        
        movie = self.db.fetch_movie("0093886")
        print movie
        self.assertEqual(movie.title, "Roxanne")
        print self.db


if __name__ == '__main__':
    test_all()
