#!/usr/bin/env python
#-*- coding:utf-8 -*-
"""Simple interface to the Atari Mania to retrieve images for games

Licence: LGPL

References:
  
"""
import os, re, urllib, time, logging

from bs4 import BeautifulSoup
import requests

from ..download import DownloadTask

class Game(object):
    def __init__(self, div=None):
        self.name = ""
        self.id = -1
        self.url = ""
        self.default_image_url = ""
        self.all_image_urls = []
        self.publisher = None
        self.publisher_id = None
        self.year = None
        self.year_id = None
        self.genre = None
        self.genre_id = None
        self.country = None
        self.country_id = None
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
    
    def split(self, href, key):
        return href.split(key)[1].split('_')[0]
    
    def __unicode__(self):
        return u"%s (%s, %s, %s): %s, %s" % (self.name, self.year, self.publisher, self.country, self.url, self.default_image_url)
    
    def __str__(self):
        return "%s (%s, %s, %s): %s, %s" % (self.name, self.year, self.publisher, self.country, self.url, self.default_image_url)

    def process_details(self, soup):
        div = soup.find(id="galleryb")
#        print div
        for img in div.find_all('img'):
            url = img.attrs['src']
#            print url
            self.all_image_urls.append(url)

class AtariMania_API(object):
    API_KEY = 'a8b9f96dde091408a03cb4c78477bd14'
    base_url = "http://www.atarimania.com/"
    image_sizes = {}
    cache_path = "/tmp"
    
    @classmethod
    def get_path(cls, rel_url):
        encoded_path = urllib.quote_plus(rel_url)
        cached = os.path.join(cls.cache_path, encoded_path)
        return cached
        
    @classmethod
    def get_url(cls, rel_url):
        return cls.base_url + rel_url
        
    @classmethod
    def getSoup(cls, rel_url):
        cached = cls.get_path(rel_url)
        if os.path.exists(cached):
            page = open(cached, "rb").read()
        else:
            page = requests.get(cls.base_url + rel_url).content
            fh = open(cached, "wb")
            fh.write(page)
            fh.close()
        return BeautifulSoup(page)
    
    @classmethod
    def encode_title(cls, title):
        return ".".join([str(ord(c)) for c in title])
    
    def search(self, title):
        path = "list_games_atari_search_%s._8_G.html" % self.encode_title(title)
        soup = self.getSoup(path)
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
                r = Game(link)
                possibilities.append(r)
        return possibilities
    
    def get_game_details(self, game):
        soup = self.getSoup(game.url)
        game.process_details(soup)


class Atari8BitTask(DownloadTask):
    def __init__(self, api, rel_url):
        self.api = api
        url = api.get_url(rel_url)
        path = api.get_path(rel_url)
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
                best = games[0]
                tasks.append(Atari8BitGetGameDetails(self.api, games[0]))
        else:
            print "Failed loading %s" % self.url
        return tasks

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
