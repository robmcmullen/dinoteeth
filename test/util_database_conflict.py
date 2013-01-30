#!/usr/bin/env python
# -*- coding: utf-8 -*-
import os, sys, time

from dinoteeth_test import *

from dinoteeth.config import setup
from dinoteeth.filescan import MediaFile
from dinoteeth.metadata import MetadataLoader

if __name__ == '__main__':
    import sys
    import logging
    
    logging.basicConfig(level=logging.DEBUG,
                        format='%(name)s: %(message)s',
                        )
    
    try:
        cfg = setup(sys.argv)
    except Exception, e:
        print "Startup failure: %s" % e
        sys.exit()
    db = cfg.db
    
    media = db.get_all("video")
    media.sort()
    f = media[0]
    key = media[0].pathname
    pos = f.scan.get_last_position() + 100
    while True:
        print f, pos
        try:
            f.scan.set_last_position(pos + 1)
        except cfg.zodb.conflict:
            print "Conflict!"
            raise
        time.sleep(4)
        print "Loading new object"
        cfg.zodb.sync()
        f = db.get(key)
        pos = f.scan.get_last_position()

