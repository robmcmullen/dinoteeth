import __builtin__

import SDL, SDL_Image, SDL_Pango

from .base import MainWindow, FontInfo, BaseImage

def escape_markup(text):
    print text
    return unicode(text).replace(u"&", u"&amp;")

class SdlMainWindow(MainWindow):
    """Main window using the ctypesgen SDL toolkit
    
    Note that this window uses a right-handed coordinate system where the
    origin is the lower left corner.  (Native SDL places the origin at the
    upper left corner.)
    
    """
    def __init__(self, config, fullscreen=True, width=800, height=600, margins=None,
                 thumbnails=None):
        SDL.SDL_Init(SDL.SDL_INIT_EVERYTHING)
        SDL_Pango.SDLPango_Init();
        SDL_Image.IMG_Init(0)
        SDL.SDL_EnableKeyRepeat(300, 100)
        self.create_screen(width, height)
        MainWindow.__init__(self, config, fullscreen, width, height, margins,
                            thumbnails)
        __builtin__._ = escape_markup

    def get_font_detail(self, name, size):
        return SdlFontInfo(name, size)
    
    ########## low level graphics routines
    
    def create_screen(self, width, height):
        self.screen = SDL.SDL_SetVideoMode(width, height, 0, 0)
        self.width = self.screen.contents.w
        self.height = self.screen.contents.h
    
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
                    self.on_key_press(ev.key.keysym.sym, ev.key.keysym.mod)
                    break
                elif ev.type == SDL.SDL_MOUSEMOTION:
                    print "mouse motion"
            
    
    def on_draw(self):
        self.clear()
        self.layout.draw()
    
    def refresh(self):
        self.layout.refresh()
        self.flip()
    
    def on_key_press(self, keycode, modifiers):
        print "key press: %s" % keycode
        self.controller.process_key_press(keycode, modifiers)
    
    def on_close(self):
        self.quit()
        
    ########## Event functions
    
    def post_event(self, event, *args):
        print "FIXME! Post event"
    
    ########## Timer functions
    
    def schedule_once(self, callback, seconds):
        print "FIXME! Schedule once"
    
    def unschedule(self, callback):
        print "FIXME! Unschedule"
    
    ########## Drawing functions
    
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
#        pyglet.graphics.draw(4, GL_QUADS, ('v2i', verts), ('c4B', background_color*4))
#        pyglet.graphics.draw(4, GL_LINE_LOOP, ('v2i', verts), ('c4B', border_color*4))
        print "FIXME: draw box"
    
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
            self.blit_surface(image.image, x, y)

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
    def free(self):
        """Free any system resources used by the image and prohibit further use
        of the image.
        
        """
        SDL.SDL_FreeSurface(self.image)
    
    def load(self, filename):
        """Load the image and set the dimensions.
        
        """
        if not filename:
            return
        self.image = SDL_Image.IMG_Load(filename)
        self.width = self.image.contents.w
        self.height = self.image.contents.h
