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
import os, urllib

from ..utils import HttpProxyBase

class TMDb3_API(HttpProxyBase):
    API_KEY = 'a8b9f96dde091408a03cb4c78477bd14'
    base_url = None
    image_sizes = {}
    
    def __init__(self, cache_dir, language, poster_size):
        HttpProxyBase.__init__(self, cache_dir)
        self.cache_dir = cache_dir
        self.movie_obj_cache = {}
        self.language = language
        self.poster_size = poster_size

    def get_cache_path(self, url):
        """Different from superclass to remove api_key from cached pathname"""
        path_part = url.split("//", 1)[1]
        if "?api_key=" in path_part:
            path_part = path_part.split("?api_key=", 1)[0]
        full_path = os.path.join(self.cache_dir, path_part)
        dir_part = os.path.dirname(full_path)
        if not os.path.exists(dir_part):
            os.makedirs(dir_part)
        return full_path

    def get_conf(self):
        if self.__class__.base_url:
            return
        url = self.get_conf_url()
        page = self.load_url(url)
        self.process_conf(page)
    
    def get_conf_url(cls):
        return "http://api.themoviedb.org/3/configuration?api_key=%s" % (cls.API_KEY)
    
    @classmethod
    def process_conf(cls, page):
        conf = cls.get_json(page)
        cls.base_url = conf['images']['base_url']
        cls.image_sizes['backdrops'] = conf['images']['backdrop_sizes']
        cls.image_sizes['posters'] = conf['images']['poster_sizes']

    movie_urls = {
        'main': "http://api.themoviedb.org/3/movie/%s?api_key=%s",
        'release_info': "http://api.themoviedb.org/3/movie/%s/releases?api_key=%s",
        'images': "http://api.themoviedb.org/3/movie/%s/images?api_key=%s",
        }
    
    def get_url_from_task(self, task, movie=None):
        if movie is not None:
            m_id = movie.tmdb_id
        else:
            m_id = task.imdb_id
        return self.movie_urls[task.info_name] % (m_id, self.API_KEY)

    def get_imdb_id_url(self, imdb_id):
        return "http://api.themoviedb.org/3/movie/%s?api_key=%s" % (imdb_id, self.API_KEY)

    def get_imdb_id(self, imdb_id):
        url = self.get_imdb_id_url(imdb_id)
        page = self.load_url(url)
        return self.get_movie(page)

    def get_movie(self, page):
        print page
        try:
            movie = self.get_json(page)
            print movie
            if 'id' in movie:
                return Movie(movie, self.language, self.poster_size)
        except Exception, e:
            print "Failed loading tmdb info: %s" % str(e)
            import traceback
            traceback.print_exc()
        return None

class Movie(TMDb3_API):
    def __init__(self, json, language, poster_size):
        self.movie = json
        self.language = language
        self.default_size = {
            'posters': poster_size,
            'backdrops': 'w1280',
            }
        self.tmdb_id = self.movie['id']
        self.image_language = None
        self.images = None
#        self.get_release_info()
    
    def process_from_task(self, task):
        page = task.data
        method = getattr(self, "process_%s" % task.info_name)
        method(page)
    
    def __str__(self):
        return simplejson.dumps(self.movie, sort_keys=True, indent=4) + simplejson.dumps(self.images, sort_keys=True, indent=4)
    
    def __unicode__(self):
        return simplejson.dumps(self.movie, sort_keys=True, indent=4) + simplejson.dumps(self.images, sort_keys=True, indent=4)
    
    def __contains__(self, key):
        return key in self.movie
    
    def __getitem__(self, key):
        if key in self.movie:
            return self.movie[key]
        raise KeyError("%s not found in TMDb data" % key)
    
    def get_release_info(self):
        url = "http://api.themoviedb.org/3/movie/%%s/releases?api_key=%s" % (self.API_KEY)
        data = self.load_url(url % (self.tmdb_id))
        self.process_release_info(data)
    
    def process_release_info(self, data):
        releases = self.get_json(data)
        print "Releases: %s" % str(releases)
        self.movie['releases'] = releases['countries']
    
    def discover_images(self):
        if self.images is not None:
            if self.image_language == self.language:
                return
        url = "http://api.themoviedb.org/3/movie/%%s/images?api_key=%s" % (self.API_KEY)
        data = self.load_url(url % (self.tmdb_id))
        self.process_images(self, data)
        
    def process_images(self, data):
        all_images = self.get_json(data)
        self.images = {}
        for key in ['backdrops', 'posters']:
            valid = []
            print key
            for image in all_images[key]:
                lang = image['iso_639_1']
                if lang is None or lang == self.language:
                    valid.append(image)
                    print image['file_path'], image['width'], image['height'], image['vote_average'], image['vote_count']
            self.images[key] = valid
        self.image_language = self.language
    
    def get_best_image(self, key, size=None):
        if self.image_language is None:
            return
        if size == None:
            size = self.default_size[key]
        elif size not in self.image_sizes[key]:
            raise KeyError
        if self.images[key]:
            print simplejson.dumps(self.images[key][0], sort_keys=True, indent=4)
            full_url = self.base_url + size + self.images[key][0]['file_path']
            return full_url
        return None
    
    def get_best_poster_url(self, size=None):
        return self.get_best_image('posters', size)
    
    def get_best_backdrop_url(self, size=None):
        return self.get_best_image('backdrops', size)
    
    def get_all_image_urls(self, key, size=None):
        thumbnails = []
        if size == None:
            size = self.default_size[key]
        elif size not in self.image_sizes[key]:
            raise KeyError
        for image in self.images[key]:
            full_url = self.base_url + size + image['file_path']
            thumbnails.append(full_url)
        return thumbnails
    
    def get_all_thumbnails(self, key):
        size = self.image_sizes[key][0] # use the smallest size
        return self.get_all_image_urls(size)
    
    def get_all_poster_urls(self, size=None):
        return self.get_all_thumbnails('posters', size)
    
    def get_all_backdrop_urls(self, size=None):
        return self.get_all_thumbnails('backdrops', size)
    
    def get_all_poster_thumbnail_urls(self):
        return self.get_all_thumbnails('posters')
    
    def get_all_backdrop_thumbnail_urls(self):
        return self.get_all_thumbnails('backdrops')


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
