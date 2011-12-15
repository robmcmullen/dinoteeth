#!/usr/bin/env python
"""
Get TMDB/IMDB metadata for movies in the database
"""

import os, os.path, sys, glob
from optparse import OptionParser

from PIL import Image
import imdb
import tempfile

import third_party.themoviedb.tmdb as tmdb
from serializer import PickleSerializerMixin


class MetadataDatabase(PickleSerializerMixin):
    def __init__(self):
        PickleSerializerMixin.__init__(self)
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

class MovieMetadataDatabase(MetadataDatabase):
    def __init__(self):
        MetadataDatabase.__init__(self)
        self.imdb_api = imdb.IMDb()
        self.tmdb_api = tmdb.MovieDb()
    
    def print_entry(self, tfilm):
        #print unicode(dict(tfilm)).encode('ascii', 'replace')
        print "Original Name: %s" % unicode(tfilm['original_name']).encode('ascii', 'replace')
        print "Released: %s" % safeprint(tfilm['released'])
        print "IMDB ID: %s" % tfilm['imdb_id']
        print "Rating: %s" % tfilm['rating']
        print "Posters:"
        biggest = None
        for poster in tfilm['images'].posters:
            for key, value in poster.items():
                if key not in ['id', 'type']:
                    print "poster: %s" % value
                    biggest = value
        print "Cast: %s" % str([safeprint(c['name'] for c in tfilm['cast'])])
        print "Categories: %s" % tfilm['categories']
        print "Certification: %s" % tfilm['certification']
        print "Genre: %s" % tfilm['categories']['genre'].keys()

    def add_info(self, movie):
        id = movie.imdb_id
        if id in self.db:
            print "Already have metadata for %s" % movie.canonical_title
            self.print_entry(self.db[id])
            return
        
        results = self.tmdb_api.search(movie.canonical_title)
        for result in results:
            imdb_id = result['imdb_id']
            if imdb_id is None:
                continue
            
            # First entry in results is assumed to be the best match
            if not movie.imdb_id:
                movie.imdb_id = imdb_id
            
            tfilm = result.info()
            self.print_entry(tfilm)
            self.db[imdb_id] = tfilm
#            
#            if imdb_id and imdb_id.startswith('tt'):
#                imdb_ttid = int(imdb_id[2:])
#                ifilm = self.imdb_api.get_movie(imdb_ttid)
#
#                print "title: %s year: %s" % (ifilm['title'].encode('ascii', 'replace'), ifilm['year'])
#
#                print dir(ifilm)
#            else:
#                print "%s not a movie ID" % imdb_id
#            print
#            print
            
#            filename = biggest.split("/")[-1]
#            (name, extension) = os.path.splitext(filename)
#            local_thumb = thumb + extension
#            if not os.path.exists(local_thumb):
#                local_file = open(local_thumb, "wb")
#                local_file.write(urllib.urlopen(biggest).read())
#                local_file.close()
#                print local_thumb
#                time.sleep(60)
            return
    
    def lookup(self, id):
        return self.db[id]

if __name__ == "__main__":
    usage="usage: %prog CMD [options] file [files...]"
    parser=OptionParser(usage=usage)
    parser.add_option("-v", action="store_true", dest="verbose", default=False)
    parser.add_option("-o", action="store", dest="output", default="index.html")
    parser.add_option("-m", "--metadata-database", action="store", dest="mdb", default="dinoteeth-metadata.db")
    parser.add_option("-d", "--database", action="store", dest="database", default="dinoteeth.db")
    parser.add_option("-i", "--image_dir", action="store", dest="imagedir", default="test/metadata")
    (options, args) = parser.parse_args()
    print options

    from config import Config
    c = Config(args)
    c.options = options
    db = c.get_database()
    print db
    mdb = MovieMetadataDatabase()
    mdb.loadStateFromFile(options.mdb)
    results = db.find("movie")
    print results
    for movie in results:
        mdb.add_info(movie)
    mdb.saveStateToFile()
    db.saveStateToFile()
