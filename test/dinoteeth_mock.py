#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os, sys
from dinoteeth.metadata.home_theater import BaseMetadata, MovieMetadata
from dinoteeth.utils import TitleKey

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
        self['title'] = "Title"
        self['canonical name'] = "Last, First"
        self.notes = ""

class MockMetadata(BaseMetadata):
    def __init__(self):
        title_key = TitleKey("video", "movie", "Title", "Year")
        BaseMetadata.__init__(self, "-123456", title_key)

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
        if title_key.title.startswith("The "):
            title_key.title = title_key.title[4:]
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
