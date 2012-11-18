#!/usr/bin/env python
#-*- coding:utf-8 -*-
"""Simple interface to the Atari Mania to retrieve images for games

Licence: LGPL

References:
  
"""
import os, re, urllib, time, logging

from bs4 import BeautifulSoup
import requests

from api_base import GameAPI
from metadata import GameMetadata, GameMetadataLoader
from ..metadata import MetadataLoader


class AtariManiaGame(GameMetadata):
    game_platform = None
    
    def __init__(self, div=None):
        GameMetadata.__init__(self, None, None)
        if div:
            self.parse_summary(div)
    
    def parse_summary(self, div):
        for link in div.find_all('a'):
#            print link
            href = link.attrs['href']
            
            # Note: must convert beautiful soup results into strings or some
            # other native type because serialization fails with an odd error:
            #
            #  File "/usr/lib64/python2.7/site-packages/ZODB/serialize.py", line 431, in _dump
            #    self._p.dump(state)
            #  File "/usr/lib64/python2.7/site-packages/ZODB/serialize.py", line 276, in persistent_id
            #    if not isinstance(obj, (Persistent, type, WeakRef)):
            #RuntimeError: maximum recursion depth exceeded while calling a Python object
            # when using savepoints in zodb, or when saving the database direcly:
            # 
            #  File "/usr/lib64/python2.7/site-packages/ZODB/serialize.py", line 431, in _dump
            #    self._p.dump(state)
            #  File "/usr/lib64/python2.7/copy_reg.py", line 74, in _reduce_ex
            #    getstate = self.__getstate__
            #  File "/usr/lib64/python2.7/site-packages/bs4/element.py", line 924, in __getattr__
            #    "'%s' object has no attribute '%s'" % (self.__class__, tag))
            #RuntimeError: maximum recursion depth exceeded while getting the str of an object

            if 'publisher_' in href:
                self.publisher_id = unicode(self.split(href, "publisher_"))
                self.publisher = unicode(link.string)
            elif 'year_' in href:
                self.year_id = unicode(self.split(href, "year_"))
                self.year = unicode(link.string)
            elif 'genre_' in href:
                self.genre_id = unicode(self.split(href, "genre_"))
                self.genre = unicode(link.string)
            elif 'country_' in href:
                self.country_id = unicode(self.split(href, "country_"))
                self.country = unicode(link.img.attrs['alt'])
            elif 'class' in link.attrs and 'preview' in link.attrs['class']:
                self.title = unicode(link.img.attrs['alt'])
                self.id = unicode(href.split("_")[1].split(".")[0])
                self.url = str(href)
                self.default_image_url = str(link.img.attrs['src'])
        self.imdb_id = str(self.id)
    
    def split(self, href, key):
        return href.split(key)[1].split('_')[0]
    
    def process_details(self, soup):
        div = soup.find(id="galleryb")
#        print div
        for img in div.find_all('img'):
            url = img.attrs['src']
#            print url
            self.all_image_urls.append(url)

class Atari8bitGame(AtariManiaGame):
    game_platform = "atari-8bit"

class AtariSTGame(AtariManiaGame):
    game_platform = "atari-st"


class AtariMania_API(GameAPI):
    base_url = "http://www.atarimania.com/"
    ignore_query_string_params = ['timestamp']
    game_platform_map = {
        "atari-8bit": '8',
        "atari-st": 'S',
        }
    image_sizes = {}
    
    def __init__(self, game_class, settings):
        self.game_class = game_class
        self.platform = self.game_platform_map[game_class.game_platform]
        GameAPI.__init__(self, settings)
    
    def get_cache_dir(self, settings):
        if hasattr(settings, "atarimania_cache_dir"):
            return settings.atarimania_cache_dir
        return "/tmp"
    
    @classmethod
    def encode_title(cls, title):
        return ".".join([str(ord(c)) for c in title])
    
    def get_soup_from_path(self, path):
        page = self.load_rel_url(path)
        return self.get_soup(page)
    
    def search(self, title):
        title, ext = os.path.splitext(title)
        while len(title) > 2:
            print "trying title -->%s<--" % title
            matches = self.autocomplete_title(title)
            if len(matches) > 0:
                return self.get_search_results(matches[0])
            title = title[:-1]
        return []
    
    def autocomplete_title(self, title):
        """Use atarimania autocomplete API to get a title
        
        Reverse engineered the URL from watching XMLHTTPRequests in Firebug.
        The param "s" is the platform and "t" is the type where "G" is for
        games.
        """
        title = title.lower()
        path = "search.php?q=%s&limit=10&timestamp=%d&s=%s&t=G" % (title, int(time.time()), self.platform)
        page = self.load_rel_url(path)
        results = []
        for line in page.splitlines():
            print "-->%s<--" % line
            if line.endswith("|"):
                line = line[:-1]
            results.append(line)
        return results
    
    def get_search_results(self, title):
        path = "list_games_atari_search_%s._%s_G.html" % (self.encode_title(title), self.platform)
        soup = self.get_soup_from_path(path)
        return self.process_search(soup)
    
    def process_search(self, soup):
        possibilities = []
        for link in soup.find_all('a'):
            if 'class' in link.attrs and 'preview' in link.attrs['class']:
                # {'href': 'game-atari-400-800-xl-xe-mule_3588.html', 'class': ['preview'], 'title': '8bit/screens/mule_6.gif'}
#                print link
                while link.name != 'div':
                    link = link.parent
#                print link
                r = self.game_class(link)
                possibilities.append(r)
        return possibilities
    
    def get_game_details(self, game):
        soup = self.get_soup_from_path(game.url)
        game.process_details(soup)


class AtariManiaLoader(GameMetadataLoader):
    def fetch_posters(self, item):
        for i, rel_url in enumerate(item.all_image_urls):
            url = self.api.get_rel_url(rel_url)
            print("image %d url: %s" % (i, url))
            data = self.api.load_url(url)
            suffix = "-screenshot%02d" % i
            self.save_poster(item, url, data, suffix)
        return None

class AtariMania8bitLoader(AtariManiaLoader):
    def init_proxies(self, settings):
        self.api = AtariMania_API(Atari8bitGame, settings)

class AtariManiaSTLoader(AtariManiaLoader):
    def init_proxies(self, settings):
        self.api = AtariMania_API(AtariSTGame, settings)

MetadataLoader.register("game", Atari8bitGame.game_platform, AtariMania8bitLoader)
MetadataLoader.register("game", AtariSTGame.game_platform, AtariManiaSTLoader)
