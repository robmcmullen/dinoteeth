#!/usr/bin/env python
#-*- coding:utf-8 -*-
"""Simple interface to the themoviedb.org version 3 API

Currently, this is used only for image retrieval.

Based on: https://github.com/doganaydin/themoviedb and https://github.com/dbr/themoviedb

Licence: LGPL

References:
  http://help.themoviedb.org/discussions/problems/121-api-v3-search-movie-by-imdb-id
  http://help.themoviedb.org/kb/api/configuration
  http://help.themoviedb.org/kb/api/movie-images
"""

try:
    import simplejson
except:
    import json as simplejson

import requests

class TMDb3_API(object):
    API_KEY = 'a8b9f96dde091408a03cb4c78477bd14'
    base_url = None
    image_sizes = {}
    
    @classmethod
    def getJSON(cls, url):
        page = requests.get(url).content
        try:
            return simplejson.loads(page)
        except:
            return simplejson.loads(page.decode('utf-8'))
    
    @classmethod
    def get_conf(cls):
        if cls.base_url:
            return
        url = "http://api.themoviedb.org/3/configuration?api_key=%s" % (cls.API_KEY)
        conf = cls.getJSON(url)
        cls.base_url = conf['images']['base_url']
        cls.image_sizes['backdrops'] = conf['images']['backdrop_sizes']
        cls.image_sizes['posters'] = conf['images']['poster_sizes']

    def get_imdb_id(self, imdb_id):
        url = "http://api.themoviedb.org/3/movie/%%s?api_key=%s" % (self.API_KEY)
        movie = self.getJSON(url % imdb_id)
        if 'id' in movie:
            return Movie(movie)
        return None

class Movie(TMDb3_API):
    def __init__(self, json):
        self.movie = json
        self.tmdb_id = self.movie['id']
        self.image_language = None
        self.images = None
        self.get_release_info()
    
    def __str__(self):
        return simplejson.dumps(self.movie, sort_keys=True, indent=4)
    
    def __unicode__(self):
        return simplejson.dumps(self.movie, sort_keys=True, indent=4)
    
    def __getitem__(self, key):
        if key in self.movie:
            return self.movie[key]
        raise KeyError("%s not found in TMDb data")
    
    def get_release_info(self):
        url = "http://api.themoviedb.org/3/movie/%%s/releases?api_key=%s" % (self.API_KEY)
        releases = self.getJSON(url % (self.tmdb_id))
        self.movie['releases'] = releases['countries']
    
    def discover_images(self, language):
        if self.images is not None:
            if self.image_language == language:
                return
        url = "http://api.themoviedb.org/3/movie/%%s/images?api_key=%s" % (self.API_KEY)
        all_images = self.getJSON(url % (self.tmdb_id))
        self.images = {}
        for key in ['backdrops', 'posters']:
            valid = []
            print key
            for image in all_images[key]:
                lang = image['iso_639_1']
                if lang is None or lang == language:
                    valid.append(image)
                    print image['file_path'], image['width'], image['height'], image['vote_average'], image['vote_count']
            self.images[key] = valid
        self.image_language = language
    
    def get_best_image(self, key, size, language):
        self.get_conf()
        self.discover_images(language)
        if size not in self.image_sizes[key]:
            raise KeyError
        if self.images[key]:
            print simplejson.dumps(self.images[key][0], sort_keys=True, indent=4)
            full_url = self.base_url + size + self.images[key][0]['file_path']
            return full_url
        return None
    
    def get_best_poster(self, size, language="en"):
        return self.get_best_image('posters', size, language)
    
    def get_best_backdrop(self, size, language="en"):
        return self.get_best_image('backdrops', size, language)
    
    def get_all_thumbnails(self, key, language):
        self.get_conf()
        self.discover_images(language)
        size = self.image_sizes[key][0]
        thumbnails = []
        for image in self.images[key]:
            full_url = self.base_url + size + image['file_path']
            thumbnails.append(full_url)
        return thumbnails
    
    def get_all_poster_thumbnails(self, language="en"):
        return self.get_all_thumbnails('posters', language)
    
    def get_all_backdrop_thumbnails(self, language="en"):
        return self.get_all_thumbnails('backdrops', language)


if __name__ == '__main__':
    import sys
    
    api = TMDb3_API()
#    t = api.get_imdb_id("tt0140352")
    t = api.get_imdb_id("tt0187489")
    if t:
        print t.get_best_poster("w92")
        print t.get_best_backdrop("w300")
        print t.get_all_poster_thumbnails()
    else:
        print "IMDb ID not found"
    sys.exit()
