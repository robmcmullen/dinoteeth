import os, time, ctypes, __builtin__

import SDL, SDL_Image, SDL_Pango, SDL_gfx

from .base import MainWindow, FontInfo, BaseImage
from ..updates import UpdateManager

def escape_markup(text):
    return unicode(text).replace(u"&", u"&amp;")

class SdlMainWindow(MainWindow):
    """Main window using the ctypesgen SDL toolkit
    
    Note that this window uses a right-handed coordinate system where the
    origin is the lower left corner.  (Native SDL places the origin at the
    upper left corner.)
    
    """
    def __init__(self, config, factory, fullscreen=True, width=800, height=600, margins=None,
                 thumbnails=None):
        os.environ["SDL_VIDEO_CENTERED"] = "1" # No other way to center windows in SDL 1.2!
        SDL.SDL_Init(SDL.SDL_INIT_EVERYTHING)
        SDL_Pango.SDLPango_Init();
        SDL_Image.IMG_Init(0)
        SDL.SDL_EnableKeyRepeat(300, 100)
        info = SDL.SDL_GetVideoInfo()
        self.monitor_size = (info.contents.current_w, info.contents.current_h)
        self.window_size = (width, height)
        self.create_screen(fullscreen)
        MainWindow.__init__(self, config, factory, fullscreen, width, height, margins,
                            thumbnails)
        __builtin__._ = escape_markup

    def get_font_detail(self, name, size):
        return SdlFontInfo(name, size)
    
    ########## low level graphics routines
    
    def create_screen(self, fullscreen):
        flags = 0
        if fullscreen:
            flags ^= SDL.SDL_FULLSCREEN
            w = self.monitor_size[0]
            h = self.monitor_size[1]
        else:
            w = self.window_size[0]
            h = self.window_size[1]
        self.screen = SDL.SDL_SetVideoMode(w, h, 0, flags)
        self.width = self.screen.contents.w
        self.height = self.screen.contents.h
        if fullscreen:
            SDL.SDL_ShowCursor(SDL.SDL_DISABLE)
    
    def set_using_external_app(self, state, fullscreen):
        MainWindow.set_using_external_app(self, state, fullscreen)
        if self.using_external_app:
            if fullscreen:
                self.create_screen(False)
        else:
            if fullscreen:
                self.create_screen(not fullscreen)
            self.layout.refresh() # refresh menu without redraw as it will be redrawn when fullscreened
            if fullscreen:
                self.create_screen(fullscreen)
    
    def get_size(self):
        return (self.width, self.height)
    
    def flip(self):
        SDL.SDL_Flip(self.screen)
    
    def clear(self):
        SDL.SDL_FillRect(self.screen, None, 0)
    
    ########## event processing
    
    def run(self):
        self.event_loop()
    
    def quit(self):
        MainWindow.quit(self)
        self.running = False
    
    def event_loop(self):
        self.running = True
        ev = SDL.SDL_Event()
        while self.running:
            self.on_draw()
            self.flip()
            while SDL.SDL_WaitEvent(SDL.pointer(ev)) == 1:
                if ev.type == SDL.SDL_KEYDOWN:
                    self.controller.process_key_press(ev.key.keysym.sym,
                                                      ev.key.keysym.mod)
                    break
                elif ev.type == SDL.SDL_MOUSEMOTION:
                    pass
                elif ev.type == SDL.SDL_QUIT:
                    self.quit()
                elif ev.type == SDL.SDL_USEREVENT:
                    argid = int(ev.user.data1)
                    user_data = self.event_data.pop(argid)
#                    print "User event! code=%d data1=%s user_data=%s" % (ev.user.code, ev.user.data1, str(user_data))
                    func_name = self.event_code_to_callback[ev.user.code]
                    callback = getattr(self, func_name)
                    retval = callback(*user_data)
                    if retval == "force redraw":
                        break
                
            UpdateManager.process_tasks()
    
    def on_draw(self):
        self.layout.draw()
    
    def refresh(self):
        self.layout.refresh()
        self.flip()
    
    ########## Event functions
    
    # Event names are used as the callback name to perform an action and are
    # stored in a mapping so that the event code can be passed through the
    # SDL_UserEvent structure.  (Also need to create the reverse mapping so
    # that the code can produce the callback name.)
    known_events = {
        'on_status_update': 1,
        'on_timer': 2,
        'on_timer_tick': 3,
        }
    event_code_to_callback = {}
    for callback, code in known_events.iteritems():
        event_code_to_callback[code] = callback
    
    # Rather that trying to marshal python arguments into the SDL event, store
    # the python event data a dict and reference it by number.
    event_data_counter = 1
    event_data = {}
    
    def post_event(self, event, *args):
        ev = SDL.SDL_Event()
        ev.type = SDL.SDL_USEREVENT
        ev.user.code = self.known_events[event]
        argcopy = tuple(args)
        argid = self.event_data_counter
        self.event_data_counter += 1
        data1 = ctypes.cast(argid, ctypes.c_void_p)
        self.event_data[argid] = argcopy
        ev.user.data1 = data1
        SDL.SDL_PushEvent(SDL.pointer(ev))
    
    ########## Timer functions
    
    scheduled = {}
    timer_resolution = .02
    
    def schedule_once(self, callback, seconds):
        scheduled_time = time.time() + seconds
        self.scheduled[callback] = scheduled_time
        UpdateManager.start_ticks(self.timer_resolution, scheduled_time)
    
    def clear_draw_iterator(self):
        self.draw_iterator = None
    
    def schedule_draw_iterator(self, iterator):
        scheduled_time = time.time() + 2000
        self.draw_iterator = iterator
        UpdateManager.start_ticks(self.timer_resolution, scheduled_time)
    
    def on_timer_tick(self, text=None):
        if self.using_external_app:
            print "ignoring status; external app in use"
        if text is not None:
            self.status_text.put(text)
            if time.time() > self.next_allowed_status_update:
                self.next_allowed_status_update = time.time() + self.status_update_interval
                #return "force redraw"
        if self.draw_iterator:
            print "draw_iterator"
            try:
                print "draw_iterator: calling"
                drawn = self.draw_iterator.next()
                print "draw_iterator: called"
            except StopIteration:
                print "draw_iterator: ended"
                scheduled_time = time.time() + 2
                UpdateManager.start_ticks(self.timer_resolution, scheduled_time)
                self.flip()
                self.draw_iterator = None
    
    def unschedule(self, callback):
        if callback in self.scheduled:
            del self.scheduled[callback]
    
    def on_timer(self, *args):
        if not self.scheduled:
            # Short circuit so that stop_ticks isn't endlessly called
            return
        now = time.time()
        still_pending = {}
        called = False
        for callback, execute_time in self.scheduled.iteritems():
            if now >= execute_time:
                callback()
                called = True
            else:
                still_pending[callback] = execute_time
        self.scheduled = still_pending
        if not self.scheduled:
            UpdateManager.stop_ticks()
        if called:
            return "force redraw"
    
    ########## Drawing functions
    
    def clip(self, x, y, w, h):
        destrect = SDL.SDL_Rect(x, self.height - y - h, w, h)
        SDL.SDL_SetClipRect(self.screen, SDL.pointer(destrect))
    
    def unclip(self):
        SDL.SDL_SetClipRect(self.screen, None)
    
    def clear_rect(self, x, y, w, h):
        destrect = SDL.SDL_Rect(x, self.height - y - h, w, h)
        print "clearing %s" % str((x, self.height - y - h, w, h))
        SDL.SDL_FillRect(self.screen, SDL.pointer(destrect), 0)
    
    def draw_text(self, text, font, x=0, y=0, bold=False, italic=False, color=None, anchor_x='left', anchor_y='bottom'):
        if bold:
            text = "<b>%s</b>" % text
        if italic:
            text = "<i>%s </i>" % text
        self.draw_markup(text, font, x, y, color, anchor_x, anchor_y)
    
    def draw_markup(self, markup, font, x=0, y=0, color=None, anchor_x='left', anchor_y='bottom', width=0):
        if color is None:
            color = (255, 255, 255, 255)
        context = SDL_Pango.SDLPango_CreateContext()
        SDL_Pango.SDLPango_SetDefaultColor(context, SDL_Pango.MATRIX_TRANSPARENT_BACK_WHITE_LETTER)
        SDL_Pango.SDLPango_SetMinimumSize(context, width, 0)
        markup = font.wrap_span(markup, color)
        SDL_Pango.SDLPango_SetMarkup(context, markup, -1)
        surface = SDL_Pango.SDLPango_CreateSurfaceDraw(context)
        self.blit_surface(surface, x, y, anchor_x, anchor_y)
        SDL.SDL_FreeSurface(surface)
        SDL_Pango.SDLPango_FreeContext(context)
    
    def draw_box(self, x, y, w, h, background_color=None, border_color=None):
        if background_color is None:
            background_color = (255, 255, 255, 255)
        if border_color is None:
            border_color = (255, 255, 255, 255)
        verts = (
            x + w, y + h,
            x, y + h,
            x, y,
            x + w, y
        )
        y = self.height - y - h
        SDL_gfx.boxRGBA(self.screen, x, y, x + w, y + h, background_color[0],
                                background_color[1], background_color[2],
                                background_color[3])
        SDL_gfx.rectangleRGBA(self.screen, x, y, x + w, y + h, border_color[0],
                                border_color[1], border_color[2],
                                border_color[3])
    
    ########## Image functions
    
    def get_image(self, filename):
        return SdlImage(filename)
    
    def blit_surface(self, surface, x, y, anchor_x='left', anchor_y='bottom'):
        """Blit the entire image to the window with upper left corner at
        the position specified.
        
        """
        w = surface.contents.w
        h = surface.contents.h
        y = self.height - y
        if anchor_y == 'bottom':
            y -= h
        elif anchor_y == 'center':
            y -= h // 2
        if anchor_x == 'center':
            x -= w // 2
        elif anchor_x == 'right':
            x -= w
        destrect = SDL.SDL_Rect(x, y, 0, 0)
        SDL.SDL_UpperBlit(surface, None, self.screen, SDL.pointer(destrect))
    
    def blit(self, image, x, y, depth=0):
        """Blit the entire image to the window with upper left corner at
        the position specified.
        
        """
        if image.is_valid():
            surface = image.get_surface()
            self.blit_surface(surface, x, y)
            
            # Free the memory used by the image and mark it as needing a reload
            # if it's used again
            image.free()

class SdlFontInfo(FontInfo):
    def calc_height(self):
        # I can't find a way to get font metrics out of SDL Pango, so create a
        # test string and see how tall it is.
        context = SDL_Pango.SDLPango_CreateContext()
        SDL_Pango.SDLPango_SetDefaultColor(context, SDL_Pango.MATRIX_TRANSPARENT_BACK_WHITE_LETTER)
        SDL_Pango.SDLPango_SetMinimumSize(context, -1, 0)
        markup = self.wrap_span(u"MQIbhgjy[|!()/?#", (255,255,255,255))
        SDL_Pango.SDLPango_SetMarkup(context, markup, -1)
        self.height = SDL_Pango.SDLPango_GetLayoutHeight(context)
        SDL_Pango.SDLPango_FreeContext(context)
    
    def get_spec(self):
        return "%s %s" % (self.name, self.size)
    
    def wrap_span(self, markup, color):
        spec = self.get_spec()
        color = "#%02x%02x%02x" % (color[0], color[1], color[2])
        markup = u"<span font='%s' foreground='%s'>%s</span>" % (spec, color, markup)
        return markup.encode('utf-8')

class SdlImage(BaseImage):
    def __init__(self, filename):
        BaseImage.__init__(self, filename)
        self.needs_reload = False
        
    def free(self):
        """Free any system resources used by the image and prohibit further use
        of the image unless reloaded.
        
        """
        SDL.SDL_FreeSurface(self.image)
        self.image = None
        self.needs_reload = True
    
    def is_valid(self):
        return self.needs_reload or self.image is not None
    
    def load(self, filename):
        """Load the image and set the dimensions.
        
        """
        if not filename:
            return
        self.filename = filename
        self.image = SDL_Image.IMG_Load(filename)
        self.width = self.image.contents.w
        self.height = self.image.contents.h
        self.needs_reload = False

    def get_surface(self):
        if self.needs_reload:
            self.load(self.filename)
        return self.image
