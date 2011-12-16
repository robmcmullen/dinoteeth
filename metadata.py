#!/usr/bin/env python
"""
Get TMDB/IMDB metadata for movies in the database
"""

import os, os.path, sys, glob

from PIL import Image
import imdb
import tempfile

import third_party.themoviedb.tmdb as tmdb
from serializer import PickleSerializerMixin


class MetadataDatabase(PickleSerializerMixin):
    def __init__(self, default_version=1):
        PickleSerializerMixin.__init__(self, default_version)
        self.create()
    
    def create(self):
        self.createVersion1()
    
    def createVersion1(self):
        self.db = {}
    
    def packVersion1(self):
        return self.db
    
    def unpackVersion1(self, data):
        self.db = data

def safeprint(s):
    if isinstance(s, basestring):
        return s.encode('utf8')
    return s

def printdict(d, indent=""):
    for k in sorted(d.keys()):
        v = d[k]
        if isinstance(v, dict):
            print "%s%s" % (indent, safeprint(k))
            printdict(v, indent="%s    %s:" % (indent, k))
        else:
            try:
                print "%s%s: %s" % (indent, k, safeprint(v))
            except UnicodeDecodeError:
                print "%s%s: unicode probs" % (indent, k)

def imdb_people(d, keyword):
    already_seen = set()
    people_objs = []
    for v in d[keyword]:
        if v not in already_seen:
            people_objs.append(v)
        already_seen.add(v)
        if len(people_objs) >= 10:
            break
    return [unicode(p) for p in people_objs]

class UnifiedMetadata(dict):
    conversion = [
        # dest, tmdb, imdb, default
        ('year', None, lambda m: m['year'], ""),
        ('title', lambda m: m['name'], lambda m: m['title'], ""),
        ('mpaa', lambda m: m['certification'], lambda m: m['mpaa'], ""),
        ('description', lambda m: m['overview'], lambda m: m['plot outline'], ""),
        ('rating', lambda m: m['rating'], lambda m: m['rating'], ""),
        ('released', lambda m: m['released'], None, ""),
        ('runtime', lambda m: m['runtime'], None, ""),
        ('genres',
         lambda m: sorted(m['categories']['genre'].keys()),
         lambda m: sorted(unicode(a) for a in m['genres']),
         [],
         ),
        ('directors',
         lambda m: [p['name'] for p in m['cast']['director']],
         lambda m: imdb_people(m, 'director'),
         [],
         ),
        ('producers',
         lambda m: [p['name'] for p in m['cast']['producer']],
         lambda m: imdb_people(m, 'producer'),
         [],
         ),
        ('writers',
         lambda m: [p['name'] for p in m['cast']['writer']],
         lambda m: imdb_people(m, 'writer'),
         [],
         ),
        ('actors',
         lambda m: [p['name'] for p in m['cast']['actor']],
         lambda m: imdb_people(m, 'cast'),
         [],
         ),
        ('music',
         lambda m: [p['name'] for p in m['cast']['music']],
         lambda m: imdb_people(m, 'original music'),
         [],
         ),
        ]
    prefer = "imdb"
     
    def __init__(self, imdb_id, tmdb=None, imdb=None):
        dict.__init__(self)
        self['imdb_id'] = imdb_id
        if tmdb is None:
            tmdb = dict()
        if imdb is None:
            imdb = dict()
        self.merge(tmdb, imdb)
    
    def merge(self, tmdb, imdb):
        t = dict()
        i = dict()
        for name, tfunc, ifunc, default in self.conversion:
            t[name] = self.get_value(tfunc, tmdb, default)
            i[name] = self.get_value(ifunc, imdb, default)
            if name == 'producers':
                print "producers", i[name]
        if self.prefer == "imdb":
            self.update(t)
            self.update_if_not_empty(i)
        else:
            self.update(i)
            self.update_if_not_empty(t)
    
    def get_value(self, func, source, default):
        if func is not None:
            try:
                value = func(source)
            except KeyError:
                value = default
        else:
            value = default
        return value
    
    def update_if_not_empty(self, other):
        for k, v in other.iteritems():
            if v:
                self[k] = v

class UnifiedMetadataDatabase(MetadataDatabase):
    def __init__(self, default_version=1):
        MetadataDatabase.__init__(self, default_version)
    
    def add_info(self, movie, movie_database):
        imdb_id = movie.imdb_id
        if imdb_id in self.db:
            print "Already have metadata for %s" % movie.canonical_title
            metadata = self.db[imdb_id]
            movie.metadata = metadata
            printdict(metadata)
            return
        
        imdb_id = movie_database.best_guess(movie)
        unified = movie_database.get_unified(imdb_id)
        self.db[imdb_id] = unified
        movie.imdb_id = imdb_id
        movie.metadata = unified
    
    def regenerate(self, movie, movie_database):
        imdb_id = movie.imdb_id
        unified = movie_database.get_unified(imdb_id)
        self.db[imdb_id] = unified
        movie.imdb_id = imdb_id
        movie.metadata = unified
    
    def lookup(self, id):
        return self.db[id]
    
    def get_blank_metadata(self):
        return UnifiedMetadata(None)


class MovieMetadataDatabase(MetadataDatabase):
    def __init__(self, default_version=2):
        MetadataDatabase.__init__(self, default_version)
        self.imdb_api = imdb.IMDb()
        self.tmdb_api = tmdb.MovieDb()
    
    def createVersion2(self):
        self.db_tmdb = {}
        self.db_imdb = {}
    
    def packVersion2(self):
        return (self.db_tmdb, self.db_imdb)
    
    def unpackVersion2(self, data):
        self.db_tmdb = data[0]
        self.db_imdb = data[1]
    
    def convertVersion1ToVersion2(self):
        print "Converting!!!!!!!!!"
        self.db_tmdb = self.db
        self.db_imdb = {}
        for imdb_id, tfilm in self.db_tmdb.iteritems():
            ifilm = self.fetch_imdb(imdb_id)
            metadata = UnifiedMetadata(imdb_id, tfilm, ifilm)
            print metadata

    def get_unified(self, imdb_id):
        tfilm = self.db_tmdb.get(imdb_id, dict())
        ifilm = self.db_imdb.get(imdb_id, dict())
        metadata = UnifiedMetadata(imdb_id, tfilm, ifilm)
        print metadata
        return metadata

    def print_entry(self, tfilm):
        #print unicode(dict(tfilm)).encode('ascii', 'replace')
        print "tmdb: imdb_id=%s  name=%s" % (tfilm['imdb_id'], unicode(tfilm['original_name']).encode('ascii', 'replace'))
        print "Posters:"
        biggest = None
        for poster in tfilm['images'].posters:
            for key, value in poster.items():
                if key not in ['id', 'type']:
                    print "  poster: %s" % value
                    biggest = value

    def best_guess(self, movie):
        best = None
        results = self.tmdb_api.search(movie.canonical_title)
        for result in results:
            imdb_id = result['imdb_id']
            if imdb_id is None:
                continue
            
            # First entry in results is assumed to be the best match
            if not best:
                best = imdb_id
            
            tfilm = result.info()
            self.print_entry(tfilm)
            self.db_tmdb[imdb_id] = tfilm
            ifilm = self.fetch_imdb(imdb_id)
        return best
    
    def fetch_imdb(self, imdb_id):
        if imdb_id in self.db_imdb:
            print "Already exists in local IMDB database"
            return self.db_imdb[imdb_id]
        if imdb_id and imdb_id.startswith('tt'):
            imdb_ttid = int(imdb_id[2:])
            ifilm = self.imdb_api.get_movie(imdb_ttid)

            print "imdb: name=%s year=%s" % (ifilm['title'].encode('ascii', 'replace'), ifilm.get('year', None))
            self.db_imdb[imdb_id] = ifilm
#            for w in ifilm['cast']:
#                print w.summary()
#                print w.billingPos
#                printdict(w.data)
        else:
            print "%s not a movie ID" % imdb_id
            ifilm = None
        return ifilm
            
#            filename = biggest.split("/")[-1]
#            (name, extension) = os.path.splitext(filename)
#            local_thumb = thumb + extension
#            if not os.path.exists(local_thumb):
#                local_file = open(local_thumb, "wb")
#                local_file.write(urllib.urlopen(biggest).read())
#                local_file.close()
#                print local_thumb
#                time.sleep(60)
