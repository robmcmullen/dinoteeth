import pyglet
from pyglet.gl import *

USE_OBJGRAPH = False
USE_HEAPY = False

if USE_OBJGRAPH:
    import objgraph
if USE_HEAPY:
    from guppy import hpy
    hp = hpy()

from .base import MainWindow
from ..thread import TaskManager

class PygletMainWindow(pyglet.window.Window, MainWindow):
    def __init__(self, config, fullscreen=True, width=800, height=600, margins=None):
        if fullscreen:
            pyglet.window.Window.__init__(self, fullscreen=fullscreen)
        else:
            pyglet.window.Window.__init__(self, width, height)
        MainWindow.__init__(self, config, fullscreen, width, height, margins)
            
        if USE_OBJGRAPH:
            objgraph.show_growth()
        if USE_HEAPY:
            print hp.heap()
        
        glEnable(GL_BLEND)
        glShadeModel(GL_SMOOTH)
        glBlendFunc(GL_SRC_ALPHA, GL_ONE)
        glDisable(GL_DEPTH_TEST)
    
    def run(self):
        pyglet.app.run()
    
    def on_draw(self):
        self.clear()
        self.layout.draw()
    
    def refresh(self):
        self.layout.refresh()
        self.flip()
    
    def on_text_motion(self, motion):
        self.controller.process_motion(motion)
        self.flip()
        if USE_OBJGRAPH:
            objgraph.show_growth()
        if USE_HEAPY:
            print hp.heap()

    def on_key_press(self, symbol, modifiers):
        self.controller.process_key_press(symbol, modifiers)
        self.flip()
        if USE_OBJGRAPH:
            objgraph.show_growth()
        if USE_HEAPY:
            print hp.heap()
    
    def on_close(self):
        self.stop()
        pyglet.window.Window.on_close(self)

PygletMainWindow.register_event_type('on_status_update')
