#!/usr/bin/env python
"""Command line script to populate dinoteeth metadata databases

"""

import os, os.path, sys, glob
from optparse import OptionParser

import tempfile

def currentPath():
    '''Returns the path in which the calling file is located.'''
    return os.path.dirname(os.path.join(os.getcwd(), sys._getframe(1).f_globals['__file__']))

def addImportPath(path):
    '''Function that adds the specified path to the import path. The path can be
    absolute or relative to the calling file.'''
    importPath = os.path.abspath(os.path.join(currentPath(), path))
    sys.path = [ importPath ] + sys.path

addImportPath('..')

from metadata import MovieMetadataDatabase, UnifiedMetadataDatabase
from config import Config

if __name__ == "__main__":
    usage="usage: %prog CMD [options] file [files...]"
    parser=OptionParser(usage=usage)
    parser.add_option("-v", action="store_true", dest="verbose", default=False)
    parser.add_option("-o", action="store", dest="output", default="index.html")
    parser.add_option("--batch-metadata-database", action="store", dest="bdb", default="dinoteeth.bdb")
    parser.add_option("-m", "--metadata-database", action="store", dest="umdb", default="dinoteeth.umdb")
    parser.add_option("-d", "--database", action="store", dest="database", default="dinoteeth.db")
    parser.add_option("-i", "--image-dir", action="store", dest="image_dir", default="test/posters")
    parser.add_option("-r", "--regenerate", action="store_true", dest="regenerate", default=False)
    parser.add_option("-p", "--posters", action="store_true", dest="posters", default=False)
    parser.add_option("-f", "--fetch", action="store_true", dest="fetch", default=False)
    (options, args) = parser.parse_args()
    print options

    from config import Config
    c = Config(args)
    c.options = options
    db = c.get_database()
    print db
        
    if args:
        for path in args:
            c.parse_dir(db, path)
        db.saveStateToFile()
    
    umdb = UnifiedMetadataDatabase()
    umdb.loadStateFromFile(options.umdb)
    
    if options.regenerate:
        results = db.find("movie")
        for i, movie in enumerate(results):
            print "%d: %s" % (i, movie)
            umdb.regenerate(movie, bdb)
        umdb.saveStateToFile()
        db.saveStateToFile()
    elif options.posters:
        bdb = MovieMetadataDatabase()
        bdb.loadStateFromFile(options.bdb)
        if not os.path.exists(options.image_dir):
            os.mkdir(options.image_dir)
        results = db.find("movie")
        for i, movie in enumerate(results):
            print "%d: %s" % (i, movie)
            bdb.fetch_poster(movie, options.image_dir)
    elif options.fetch:
        bdb = MovieMetadataDatabase()
        bdb.loadStateFromFile(options.bdb)
        results = db.find("movie")
        for i, movie in enumerate(results):
            print "%d: %s" % (i, movie)
            umdb.add_info(movie, bdb)
        umdb.saveStateToFile()
        bdb.saveStateToFile()
        db.saveStateToFile()
    else:
        results = db.find("movie")
        for i, movie in enumerate(results):
            print "%d: %s" % (i, movie)
            print "  group key: %s" % str(movie.group_key)
            print "  metadata: %s" % str(movie.metadata)
            print "  scanned: %s" % str(movie.scanned_metadata)
            print
        sys.exit()
