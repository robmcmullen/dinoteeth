import os

from media import MediaObject, MediaResults
from serializer import PickleSerializerMixin


class MediaScanner(object):
    def __init__(self, filename):
        self.filename = filename
        self.reset()
    
    def reset(self):
        self.audio_order = []
        self.audio = {}
        self.subtitles_order = []
        self.subtitles = {}
        self.length = 0.0
    
    def iter_audio(self):
        for id in self.audio_order:
            yield self.audio[id]
    
    def iter_subtitles(self):
        for id in self.subtitles_order:
            yield self.subtitles[id]


class Database(object):
    def __init__(self, aliases=None, media_scanner=None, **kwargs):
        if aliases is None:
            aliases = dict()
        self.aliases = aliases
        if media_scanner is None:
            media_scanner = MediaScanner
        self.media_scanner = media_scanner
        self.create()
    
    def create(self):
        pass


class DictDatabase(Database, PickleSerializerMixin):
    def __init__(self, **kwargs):
        PickleSerializerMixin.__init__(self, **kwargs)
        Database.__init__(self, **kwargs)
        
    def create(self):
        self.createVersion1()
    
    def createVersion1(self):
        self.cats = {}
    
    def packVersion1(self):
        return self.cats
    
    def unpackVersion1(self, data):
        self.cats = data
    
    def is_current(self, pathname):
        media = self.find_any_category(pathname)
        if not media:
            return False
        return media.mtime == os.stat(pathname).st_mtime
    
    def find_any_category(self, pathname):
        for category in self.cats.iterkeys():
            if pathname in self.cats[category]:
                return self.cats[category][pathname]
        return None
    
    def add(self, g):
        media = MediaObject.convertGuess(g)
        media.scan(self.media_scanner)
        category = media['type']
        if category is not None:
            if category in self.aliases:
                category = self.aliases[category]
            if category not in self.cats:
                self.cats[category] = {}
            
            self.cats[category][media['pathname']] = media
    
    def find(self, category, criteria=None):
        results = MediaResults()
        if category in self.cats:
            cat = self.cats[category]
            if criteria is None:
                criteria = lambda s: True
            for item in cat.itervalues():
                valid = criteria(item)
                if valid:
                    results.append(item)
            results.sort()
        return results
