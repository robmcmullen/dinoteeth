#!/usr/bin/env python
"""
Process a list of images, creating copies in multiple resolutions for
use as thumbnails and web-sized images.
"""

import os, os.path, sys, glob, subprocess
from optparse import OptionParser

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..")) # to find thumbnail.py
from dinoteeth.thumbnail import ThumbnailFactory

def delete(path, factory):
    thumb_file = factory.get_thumbnail_file(path)
    print path, thumb_file
    factory.delete_thumbnail(path)

if __name__ == "__main__":
    usage="usage: %prog CMD [options] file [files...]"
    parser=OptionParser(usage=usage)
    parser.add_option("-v", action="store_true", dest="verbose", default=False)
    parser.add_option("-f", action="store", dest="from_file", default=None)
    (options, args) = parser.parse_args()

    factory = ThumbnailFactory()
    thumbmap = {}
    
    if options.from_file:
        fh = open(options.from_file)
        for line in fh.readlines():
            path = line.strip()
            if path:
                delete(path, factory)
    
    for name in args:
        if os.path.isdir(name):
            print "dir %s" % name
        else:
            delete(name, factory)
