import os, Queue

from ..thread import TaskManager

class MainWindow(object):
    def __init__(self, config, fullscreen=True, width=800, height=600, margins=None):
        if margins is None:
            margins = (0, 0, 0, 0)
        self.get_fonts(config)
        self.layout = config.get_layout(self, margins)
        root = config.get_root(self)
        self.layout.set_root(root)
        self.controller = self.layout.get_controller()
        self.status_text = Queue.Queue()
        self.using_external_app = False
    
    def get_fonts(self, config):
        self.font = self.get_font_detail(config.get_font_name(),
                                         config.get_font_size())
        self.detail_font = self.get_font_detail(config.get_font_name(),
                                                config.get_detail_font_size())
        self.selected_font = self.get_font_detail(config.get_font_name(),
                                                  config.get_selected_font_size())

    def get_font_detail(self, name, size):
        raise RuntimeError("Abstract method")
    
    def run(self):
        """Start the event processing loop for the particular windowing system.
        
        """
        raise RuntimeError("Abstract method")
    
    def stop(self):
        """Cleanup after the event processing loop is exited.
        
        """
        TaskManager.stop_all()
    
    def on_status_update(self, text):
        if self.using_external_app:
            print "ignoring status; external app in use"
        else:
            self.status_text.put(text)
    
    def set_using_external_app(self, state):
        self.using_external_app = state
    
    def on_status_change(self, *args):
        if self.using_external_app:
            print "ignoring status; external app in use"
        else:
            print "clearing status bar"
        # Simply calling this function seems to generate an on_draw event, so
        # no need to call self.flip
    
    ########## Drawing functions
    
    def draw_text(self, text, font, x=0, y=0, bold=False, italic=False, color=None, anchor_x='left', anchor_y='bottom'):
        raise RuntimeError("Abstract method")
    
    def draw_box(self, x, y, w, h, background_color=None, border_color=None):
        raise RuntimeError("Abstract method")


class FontInfo(object):
    def __init__(self, name, size):
        self.name = name
        self.size = size
        self.height = None
        self.calc_height()
    
    def calc_height(self):
        raise RuntimeError("Abstract method")
