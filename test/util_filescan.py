#!/usr/bin/env python
# -*- coding: utf-8 -*-
import os, sys

from dinoteeth_test import *

from dinoteeth.config import setup

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
    
    count = 0
    for f in media:
#        print f, f.scan.selected_subtitle_id, f.scan.position
        if f.scan.position == 0:
            f.scan.selected_subtitle_id = None
        if len(f.scan.audio) > 0:
            if hasattr(f.scan.audio[0], 'title'):
                count += 1
                #print "%s: needs converting" % f
                old_scan = f.scan
                f.reset()
                f.scan.copy_stats_from(old_scan)
                print "%s: converted to: %s" % (f, f.scan.audio[0])
            else:
                print "%s: %s" % (f, f.scan.audio[0])
    print "%d/%d needs converting" % (count, len(media))
#    sys.exit()
    db.zodb.commit()