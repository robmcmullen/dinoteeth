#!/usr/bin/env python2.6

# Application start and main window for media player

import sys

from config import setup

def run():
    cfg = setup(sys.argv)
    window = cfg.get_main_window()
    try:
        window.run()
    except Exception, e:
        import traceback
        traceback.print_exc()
        
        print "Halting threads..."
        cfg.do_shutdown_tasks()
