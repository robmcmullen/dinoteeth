#!/usr/bin/env python
# -*- coding: utf-8 -*-

from dinoteeth_test import *
from dinoteeth_mock import *

from dinoteeth.database import MediaScanDatabase
from dinoteeth.utils import iter_dir

class TestDatabaseMovies1(TestCase):
    def setUp(self):
        self.db = MediaScanDatabase(mock=True)
        self.mmdb = MockMMDB()
        self.artwork_loader = MockArtworkLoader()
        self.path_dict = {"movies1": "basename, movies"}
        self.db.update_metadata(self.path_dict, self.mmdb, self.artwork_loader)
        
    def testSize(self):
        self.assertEqual(len(self.db.db), 38)
        self.assertEqual(len(self.db.title_key_map), 14)
        
    def testRemove(self):
        self.db.remove("movies1/The_Social_Network-x01.mkv", self.mmdb)
        self.assertEqual(len(self.db.db), 37)
        self.assertEqual(len(self.db.title_key_map), 14)
        
    def testUpdateMetadata(self):
        keys = set(["movies1/The_Social_Network-x01.mkv"])
        print self.db.db.keys()
        self.db.remove_metadata(keys, self.mmdb)
        self.assertEqual(len(self.db.db), 37)
        self.assertEqual(len(self.db.title_key_map), 14)
        keys = set(["movies1/The_Hunt_for_Red_October.mkv", "movies1/The_Hunt_for_Red_October-x01.mkv", ])
        print self.db.db.keys()
        self.db.remove_metadata(keys, self.mmdb)
        self.assertEqual(len(self.db.db), 35)
        self.assertEqual(len(self.db.title_key_map), 13)
        self.db.update_metadata(self.path_dict, self.mmdb, self.artwork_loader)
        print self.db.db.keys()
        self.assertEqual(len(self.db.db), 38)
        self.assertEqual(len(self.db.title_key_map), 14)
        self.db.update_metadata(self.path_dict, self.mmdb, self.artwork_loader, valid_extensions=["x01.mkv"])
        print self.db.db.keys()
        self.assertEqual(len(self.db.db), 3)
        self.assertEqual(len(self.db.title_key_map), 3)
        
    def testSameTitleKey(self):
        path_dict = {"movies1a": "basename, movies"}
        path_dict.update(self.path_dict)
        save = len(self.db.imdb_to_title_key)
        self.db.update_metadata(path_dict, self.mmdb, self.artwork_loader)
        self.assertEqual(len(self.db.db), 39)
        self.assertEqual(len(self.db.title_key_map), 15)
        self.assertEqual(len(self.db.imdb_to_title_key), save)

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
    

if __name__ == '__main__':
    test_all()
