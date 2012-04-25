import os, Queue

class MainWindow(object):
    def __init__(self, config, fullscreen=True, width=800, height=600, margins=None,
                 thumbnails=None):
        if margins is None:
            margins = (0, 0, 0, 0)
        self.get_fonts(config)
        self.layout = config.get_layout(self, margins)
        root = config.get_root(self)
        self.layout.set_root(root)
        self.controller = self.layout.get_controller()
        self.status_text = Queue.Queue()
        self.using_external_app = False
        self.app_config = config
        self.thumbnail_loader = thumbnails
    
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
    
    def quit(self):
        """Cleanup after the event processing loop is exited.
        
        """
        self.app_config.do_shutdown_tasks()
    
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
    
    ########## Event functions
    
    def post_event(self, event, *args):
        """Thread-safe call to post an event to the event queue
        
        """
        raise RuntimeError("Abstract method")
    
    ########## Timer functions
    
    def schedule_once(self, callback, seconds):
        """Schedule a callback for some number of seconds in the future
        
        """
        raise RuntimeError("Abstract method")
    
    def unschedule(self, callback):
        """Remove a scheduled callback
        
        """
        raise RuntimeError("Abstract method")
    
    ########## Drawing functions
    
    def draw_text(self, text, font, x=0, y=0, bold=False, italic=False, color=None, anchor_x='left', anchor_y='bottom'):
        raise RuntimeError("Abstract method")
    
    def draw_markup(self, markup, font, x=0, y=0, color=None, anchor_x='left', anchor_y='bottom', width=0):
        """Display an html-like markup format based on the pango markup
        language.
        
        See: http://developer.gnome.org/pango/unstable/PangoMarkupFormat.html
        
        Note that this markup language respects carriage returns; one return
        character will force a new line, and multiple consecutive characters
        will be honored.
        """
        raise RuntimeError("Abstract method")
    
    def draw_box(self, x, y, w, h, background_color=None, border_color=None):
        raise RuntimeError("Abstract method")
    
    ########## Image functions
    
    def get_image(self, filename):
        raise RuntimeError("Abstract method")
    
    def get_thumbnail_file(self, filename):
        thumbpath = self.thumbnail_loader.get_thumbnail_file(filename)
        return thumbpath
    
    def get_thumbnail_image(self, filename):
        thumbpath = self.get_thumbnail_file(filename)
        return self.get_image(thumbpath)
    
    def blit(self, image, x, y, depth=0):
        """Blit the entire image to the window with upper left corner at
        the position specified.
        
        """
        raise RuntimeError("Abstract method")


class FontInfo(object):
    def __init__(self, name, size):
        self.name = name
        self.size = size
        self.height = None
        self.calc_height()
    
    def calc_height(self):
        raise RuntimeError("Abstract method")

class BaseImage(object):
    def __init__(self, filename):
        self.width = 0
        self.height = 0
        self.image = None
        self.load(filename)
    
    def is_valid(self):
        return self.image is not None
    
    def free(self):
        """Free any system resources used by the image and prohibit further use
        of the image.
        
        """
        pass
    
    def load(self, filename):
        """Load the image and set the dimensions.
        
        """
        raise RuntimeError("Abstract method")
