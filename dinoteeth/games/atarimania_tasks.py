#!/usr/bin/env python
#-*- coding:utf-8 -*-
"""Simple interface to the Atari Mania to retrieve images for games

Licence: LGPL

References:
  
"""
import os, re, urllib, time, logging

from bs4 import BeautifulSoup

from ..download import DownloadTask


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
