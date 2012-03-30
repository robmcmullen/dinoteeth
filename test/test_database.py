#!/usr/bin/env python
# -*- coding: utf-8 -*-

from dinoteeth_test import *

from dinoteeth.database import MediaScanDatabase
from dinoteeth.utils import iter_dir

class MockMovie(object):
    def __init__(self, imdb_id):
        self.id = imdb_id
        
class MockMMDB(object):
    imdb_index = 1
    def __init__(self):
        self.title_keys = {}
        self.imdb_list = set()
        
    def remove(self, imdb_id):
        self.imdb_list.discard(imdb_id)
        
    def best_guess_from_media_scans(self, title_key, scans):
        if title_key[0].startswith("The "):
            title_key = (title_key[0][4:], title_key[1], title_key[2])
        print title_key
        if title_key not in self.title_keys:
            self.title_keys[title_key] = "tt%07d" % self.imdb_index
            self.imdb_index += 1
        imdb_id = self.title_keys[title_key]
        self.imdb_list.add(imdb_id)
        return MockMovie(imdb_id)
    
    def contains_imdb_id(self, imdb_id):
        return imdb_id in self.imdb_list
    
    def saveStateToFile(self):
        pass

class MockArtworkLoader(object):
    def has_poster(self, imdb_id):
        return True

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
    

if __name__ == '__main__':
    test_all()
