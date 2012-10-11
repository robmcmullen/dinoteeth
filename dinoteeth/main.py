#!/usr/bin/env python2.6

# Application start and main window for media player

import sys

from config import setup

def run():
    try:
        cfg = setup(sys.argv)
    except Exception, e:
        print "Startup failure: %s" % e
        return
    window = cfg.get_main_window()
    try:
        window.run()
    except Exception, e:
        import traceback
        traceback.print_exc()
        
        print "Halting threads..."
        cfg.do_shutdown_tasks()

def run_monitor():
    try:
        cfg = setup(sys.argv)
    except Exception, e:
        print "Startup failure: %s" % e
        return
    cfg.start_update_monitor()
