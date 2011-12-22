#!/usr/bin/env python2.6

# Application start and main window for media player

import sys
import pyglet

from config import setup


if __name__ == "__main__":
    cfg = setup(sys.argv)
    window = cfg.get_main_window()
    pyglet.app.run()
