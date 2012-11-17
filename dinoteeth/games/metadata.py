#!/usr/bin/env python
"""
Get TMDB/IMDB metadata for movies in the database
"""

import os, re, time, collections, logging
from ..third_party.sentence import first_sentence

from persistent import Persistent

from .. import utils

from ..metadata import MetadataLoader
from .. import settings
from api_base import GameAPI

log = logging.getLogger("dinoteeth.metadata")
log.setLevel(logging.DEBUG)


def safestr(s):
    if isinstance(s, basestring):
        return unicode(s).encode('utf-8')
    return s



class GameMetadata(Persistent):
    media_category = "games"
    game_platform = None

    def __init__(self, id, title):
        self.id = id
        self.title = title
        self.year = None
        self.imdb_id = None
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
    
    def __unicode__(self):
        return u"%s (%s, %s, %s): %s, %s" % (self.title, self.year, self.publisher, self.country, self.url, self.default_image_url)
    
    def __str__(self):
        return "%s (%s, %s, %s): %s, %s" % (self.title, self.year, self.publisher, self.country, self.url, self.default_image_url)
    
    def get_path_prefix(self, metadata_root_dir):
        return os.path.join(metadata_root_dir, self.media_category, self.game_platform)
    
    def update_with_media_files(self, media_files):
        pass
    
    def merge_database_objects(self, db):
        pass
        
    def get_markup(self, media_file=None):
        title = self.title
        if self.year:
            title += u" (%s)" % self.year
        text = u"<b>%s</b>\n" % _(title)
        if media_file:
            text += u"\nmedia file: %s" % media_file
        else:
            text += u"\nno media file specified"
        return text


class GameMetadataLoader(MetadataLoader):
    api_class = None
    
    def init_proxies(self, settings):
        self.api = self.api_class(settings)

    def search(self, title_key):
        title = title_key.title
        results = []
        try:
            results = self.api.search(title)
        except:
            log.info("Failed looking up %s" % title)
            #return None
            raise
        return results
    
    def get_metadata(self, game):
        self.api.get_game_details(game)
        return game
    
    def best_guess(self, title_key, scans):
        guesses = self.search(title_key)
        if not guesses:
            log.error("No guesses for %s???" % title_key.title)
            return GameMetadata(None, title_key)
        return self.get_metadata(guesses[0])
