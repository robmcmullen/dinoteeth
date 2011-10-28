#!/usr/bin/env python2.6

# Application start and main window for media player

import sys
import pyglet

from config import setup


class MainWindow(pyglet.window.Window):
    def __init__(self, config, width=1280, height=720):
        super(MainWindow, self).__init__(width, height)
        self.root = config.get_root(self)
        self.layout = config.get_layout(self)
    
    def on_draw(self):
        print "draw"
        self.clear()
        self.layout.draw(self.root)
    
    def on_text_motion(self, motion):
        print "here"
        self.root.process_motion(motion, self.layout)
        self.flip()

    def on_key_press(self, symbol, modifiers):
        print symbol
        self.root.process_key_press(symbol, modifiers, self.layout)
        self.flip()
        
if __name__ == "__main__":
    cfg = setup(sys.argv)
    window = MainWindow(cfg)
    pyglet.app.run()
