#!/usr/bin/env python
#-*- coding:utf-8 -*-
"""Simple interface to the Atari Mania to retrieve images for games

Licence: LGPL

References:
  
"""
import os, re, urllib, time, logging

from bs4 import BeautifulSoup
import requests

from api_base import Game, GameAPI
from ..download import DownloadTask

class Atari8bitGame(Game):
    subcategory = "atari-8bit"
    
    def __init__(self, div=None):
        Game.__init__(self)
        if div:
            self.parse_summary(div)
    
    def parse_summary(self, div):
        for link in div.find_all('a'):
#            print link
            href = link.attrs['href']
            if 'publisher_' in href:
                self.publisher_id = self.split(href, "publisher_")
                self.publisher = link.string
            elif 'year_' in href:
                self.year_id = self.split(href, "year_")
                self.year = link.string
            elif 'genre_' in href:
                self.genre_id = self.split(href, "genre_")
                self.genre = link.string
            elif 'country_' in href:
                self.country_id = self.split(href, "country_")
                self.country = link.img.attrs['alt']
            elif 'class' in link.attrs and 'preview' in link.attrs['class']:
                self.name = link.img.attrs['alt']
                self.id = href.split("_")[1].split(".")[0]
                self.url = href
                self.default_image_url = link.img.attrs['src']
        self.imdb_id = "am%s" % self.id
    
    def split(self, href, key):
        return href.split(key)[1].split('_')[0]
    
    def process_details(self, soup):
        div = soup.find(id="galleryb")
#        print div
        for img in div.find_all('img'):
            url = img.attrs['src']
#            print url
            self.all_image_urls.append(url)

class AtariMania_API(GameAPI):
    subcategory = "atari-8bit"
    
    API_KEY = 'a8b9f96dde091408a03cb4c78477bd14'
    base_url = "http://www.atarimania.com/"
    image_sizes = {}
    
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
        The param "s" is the platform: '8' for 8-bit search, 'S' for ST search.
        """
        title = title.lower()
        path = "search.php?q=%s&limit=10&timestamp=%d&s=8&t=G" % (title, int(time.time()))
        page = self.load_rel_url(path, use_cache=False)
        results = []
        for line in page.splitlines():
            print "-->%s<--" % line
            if line.endswith("|"):
                line = line[:-1]
            results.append(line)
        return results
    
    def get_search_results(self, title):
        path = "list_games_atari_search_%s._8_G.html" % self.encode_title(title)
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
                r = Atari8bitGame(link)
                possibilities.append(r)
        return possibilities
    
    def get_game_details(self, game):
        soup = self.get_soup_from_path(game.url)
        game.process_details(soup)


class Atari8BitTask(DownloadTask):
    def __init__(self, api, rel_url):
        self.api = api
        url = api.get_rel_url(rel_url)
        path = api.get_cache_path(url)
        DownloadTask.__init__(self, url, path)

class Atari8BitSearch(Atari8BitTask):
    def __init__(self, api, title):
        rel_url = "list_games_atari_search_%s._8_G.html" % AtariMania_API.encode_title(title)
        Atari8BitTask.__init__(self, api, rel_url)
        self.title = title
        print "searching %s from %s -> %s" % (title, self.url, self.path)
    
    def success_callback(self):
        print "post processing 8 bit search for '%s'" % self.title
        tasks = []
        if os.path.exists(self.path):
            page = open(self.path, "rb").read()
            soup = BeautifulSoup(page)
            games = self.api.process_search(soup)
            for game in games:
                print game
            if games:
                self.game = games[0]
                tasks.append(Atari8BitGetGameDetails(self.api, self.game))
        else:
            print "Failed loading %s" % self.url
        return tasks
    
    def subtasks_complete_callback(self):
        print "All subtasks complete: %s  Full game details:" % str(self.children_scheduled)
        print self.game

class Atari8BitGetGameDetails(Atari8BitTask):
    def __init__(self, api, game):
        Atari8BitTask.__init__(self, api, game.url)
        self.game = game
        print "details for %s from %s -> %s" % (game.name, self.url, self.path)
    
    def success_callback(self):
        print "post processing game detail for '%s'" % self.game.name
        tasks = []
        if os.path.exists(self.path):
            page = open(self.path, "rb").read()
            soup = BeautifulSoup(page)
            self.game.process_details(soup)
            for screenshot in self.game.all_image_urls:
                tasks.append(Atari8BitScreenshot(self.api, self.game, screenshot))
        else:
            print "Failed loading %s" % self.url
        return tasks

class Atari8BitScreenshot(Atari8BitTask):
    def __init__(self, api, game, screenshot_url):
        Atari8BitTask.__init__(self, api, screenshot_url)
        self.game = game
        print "screenshot for %s from %s -> %s" % (game.name, self.url, self.path)
