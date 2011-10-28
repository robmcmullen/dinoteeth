#!/usr/bin/env python2.6

# Application start and main window for media player

import sys
import pyglet

from config import setup


class MainWindow(pyglet.window.Window):
    def __init__(self, config, width=1280, height=720):
        super(MainWindow, self).__init__(width, height)
        self.layout = config.get_layout(self)
        root = config.get_root(self)
        self.layout.set_root(root)
        self.controller = self.layout.get_controller()
    
    def on_draw(self):
        print "draw"
        self.clear()
        self.layout.draw()
    
    def on_text_motion(self, motion):
        print "here"
        self.controller.process_motion(motion)
        self.flip()

    def on_key_press(self, symbol, modifiers):
        print symbol
        self.controller.process_key_press(symbol, modifiers)
        self.flip()
        
if __name__ == "__main__":
    cfg = setup(sys.argv)
    window = MainWindow(cfg)
    pyglet.app.run()
