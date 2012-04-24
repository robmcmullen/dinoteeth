#!/usr/bin/env python2.6

# Application start and main window for media player

import sys

from config import setup

def run():
    cfg = setup(sys.argv)
    window = cfg.get_main_window()
    window.run()
