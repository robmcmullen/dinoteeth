#!/usr/bin/env python
# -*- coding: utf-8 -*-
import os, sys, datetime, calendar

from dinoteeth_test import *

from dinoteeth.config import setup

def play_date(item):
    if item.scan.play_date is None:
        return 0
    # Need to return unix timestamp
    return calendar.timegm(item.scan.play_date.utctimetuple())

# from http://stackoverflow.com/questions/510357/python-read-a-single-character-from-the-user
def getch():
    import sys, tty, termios
    fd = sys.stdin.fileno()
    old_settings = termios.tcgetattr(fd)
    try:
        tty.setraw(sys.stdin.fileno())
        ch = sys.stdin.read(1)
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
    return ch

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
    
    found_mistakes = False
    for m in media:
        if hasattr(m, 'play_date'):
            print m
            delattr(m, 'play_date')
            found_mistakes = True
        if isinstance(m.scan.play_date, int):
            print m
            m.scan.play_date = None
            found_mistakes = True
    if found_mistakes:
        db.zodb.commit()
    
    show_all = True

    fake_date = datetime.datetime(1999,12,31)
    unique, scans_in_each = media.get_unique_metadata_with_value(play_date)
    order = unique.keys()
    order.sort()
    print "Press 'p' to mark played, 'n' for never played, and 'q' to quit or any other key to skip"
    for metadata in order:
        t = unique[metadata]
        if t == 0 or show_all:
            print t, unicode(metadata).encode('utf-8')
            ch = getch()
            if ch == 'q' or ord(ch) == 27:
                sys.exit()
            if ch == 'p':
                for s in scans_in_each[metadata]:
                    s.scan.play_date = fake_date
                db.zodb.commit()
            elif ch == 'n':
                for s in scans_in_each[metadata]:
                    s.scan.play_date = None
                db.zodb.commit()
