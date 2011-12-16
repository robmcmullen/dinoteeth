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
    parser.add_option("--batch-metadata-database", action="store", dest="bdb", default="dinoteeth-batch-metadata.db")
    parser.add_option("-m", "--metadata-database", action="store", dest="mdb", default="dinoteeth-unified-metadata.db")
    parser.add_option("-d", "--database", action="store", dest="database", default="dinoteeth.db")
    parser.add_option("-i", "--image-dir", action="store", dest="image_dir", default="test/posters")
    parser.add_option("-r", "--regenerate", action="store_true", dest="regenerate", default=False)
    parser.add_option("-p", "--posters", action="store_true", dest="posters", default=False)
    (options, args) = parser.parse_args()
    print options

    from config import Config
    c = Config(args)
    c.options = options
    db = c.get_database()
    print db
    bdb = MovieMetadataDatabase()
    bdb.loadStateFromFile(options.bdb)
    mdb = UnifiedMetadataDatabase()
    mdb.loadStateFromFile(options.mdb)
    
    if options.regenerate:
        results = db.find("movie")
        print results
        for movie in results:
            mdb.regenerate(movie, bdb)
        mdb.saveStateToFile()
        db.saveStateToFile()
    elif options.posters:
        if not os.path.exists(options.image_dir):
            os.mkdir(options.image_dir)
        results = db.find("movie")
        print results
        for movie in results:
            bdb.fetch_poster(movie, options.image_dir)
    else:
        results = db.find("movie")
        print results
        for movie in results:
            mdb.add_info(movie, bdb)
        mdb.saveStateToFile()
        bdb.saveStateToFile()
        db.saveStateToFile()
