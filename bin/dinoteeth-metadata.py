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
from utils import ArtworkLoader

if __name__ == "__main__":
    from config import Config
    parser = Config.get_arg_parser()
    parser.add_option("--batch-metadata-database", action="store", dest="bdb", default="dinoteeth.bdb")
    parser.add_option("-r", "--regenerate", action="store_true", dest="regenerate", default=False)
    parser.add_option("-p", "--posters", action="store_true", dest="posters", default=False)
    parser.add_option("-f", "--fetch", action="store_true", dest="fetch", default=False)
    
    c = Config(sys.argv, parser)
    db = c.db
    umdb = c.umdb
    options = c.options
    
    if options.regenerate:
        bdb = MovieMetadataDatabase()
        bdb.loadStateFromFile(options.bdb)
        results = db.find("movie")
        for i, movie in enumerate(results):
            print "%d: %s" % (i, movie)
            movie.normalize()
            umdb.regenerate(movie, bdb)
        umdb.saveStateToFile()
        db.saveStateToFile()
    elif options.posters:
        bdb = MovieMetadataDatabase()
        bdb.loadStateFromFile(options.bdb)
        loader = ArtworkLoader(options.image_dir)
        results = db.find("movie")
        for i, movie in enumerate(results):
            print "%d: %s" % (i, movie)
            bdb.fetch_poster(movie, loader.poster_dir)
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
