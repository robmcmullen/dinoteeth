import os, Queue, functools, time

class MainWindow(object):
    def __init__(self, config, factory, fullscreen=True, width=800, height=600, margins=None,
                 thumbnails=None):
        if margins is None:
            margins = (0, 0, 0, 0)
        self.get_fonts(config)
        self.layout = factory.get_layout(self, margins, config)
        root = config.get_root(self)
        self.layout.set_root(root)
        self.controller = self.layout.get_controller()
        self.status_text = Queue.Queue()
        self.next_allowed_status_update = time.time()
        self.status_update_interval = 1.0 # number of seconds before allowing a new status update
        self.using_external_app = False
        self.app_config = config
        self.thumbnail_loader = thumbnails
        self.draw_iterator = None
    
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
    
    def on_status_update(self, text=None):
        if self.using_external_app:
            print "ignoring status; external app in use"
        elif text is not None:
            self.status_text.put(text)
            if time.time() > self.next_allowed_status_update:
                self.next_allowed_status_update = time.time() + self.status_update_interval
                return "force redraw"
    
    def on_timer_tick(self, text=None):
        if self.using_external_app:
            print "ignoring status; external app in use"
    
    def set_using_external_app(self, state, fullscreen):
        self.using_external_app = state
    
    def on_status_change(self, *args):
        if self.using_external_app:
            print "ignoring status; external app in use"
        else:
            print "clearing status bar"
        # Simply calling this function seems to generate an on_draw event, so
        # no need to call self.flip
    
    ########## Event functions
    
    def get_event_callback(self, event):
        callback = functools.partial(self.post_event, event)
        return callback
    
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
    
    def clip(self, x, y, w, h):
        raise RuntimeError("Abstract method")
    
    def unclip(self):
        raise RuntimeError("Abstract method")
    
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
