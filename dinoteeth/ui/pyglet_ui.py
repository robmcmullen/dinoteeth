import pyglet
from pyglet.gl import *

USE_OBJGRAPH = False
USE_HEAPY = False

if USE_OBJGRAPH:
    import objgraph
if USE_HEAPY:
    from guppy import hpy
    hp = hpy()

from .base import MainWindow, FontInfo
import keycodes as k

class PygletMainWindow(pyglet.window.Window, MainWindow):
    to_keycode = {}
    to_modifier = {}
    
    def __init__(self, config, fullscreen=True, width=800, height=600, margins=None):
        if fullscreen:
            pyglet.window.Window.__init__(self, fullscreen=fullscreen)
        else:
            pyglet.window.Window.__init__(self, width, height)
        MainWindow.__init__(self, config, fullscreen, width, height, margins)
        
        self.create_keycode_maps()
        
        if USE_OBJGRAPH:
            objgraph.show_growth()
        if USE_HEAPY:
            print hp.heap()
        
        glEnable(GL_BLEND)
        glShadeModel(GL_SMOOTH)
        glBlendFunc(GL_SRC_ALPHA, GL_ONE)
        glDisable(GL_DEPTH_TEST)

    def get_font_detail(self, name, size):
        return PygletFontInfo(name, size)
    
    def run(self):
        pyglet.app.run()
    
    def on_draw(self):
        self.clear()
        self.layout.draw()
    
    def refresh(self):
        self.layout.refresh()
        self.flip()
    
    def on_key_press(self, symbol, modifiers):
        keycode = self.convert_keycode(symbol)
        modifiers = self.convert_keycode(modifiers)
        print "key press: %s" % keycode
        self.controller.process_key_press(keycode, modifiers)
        self.flip()
        if USE_OBJGRAPH:
            objgraph.show_growth()
        if USE_HEAPY:
            print hp.heap()
    
    def on_close(self):
        self.stop()
        pyglet.window.Window.on_close(self)
    
    ########## Keyboard functions
    
    @classmethod
    def create_keycode_maps(cls):
        pk = pyglet.window.key
        cls.to_modifier = {
            pk.MOD_SHIFT: k.MOD_SHIFT,
            pk.MOD_CTRL: k.MOD_CTRL,
            pk.MOD_ALT: k.MOD_ALT,
            pk.MOD_CAPSLOCK: k.MOD_CAPS,
            pk.MOD_NUMLOCK: k.MOD_NUM,
            pk.MOD_WINDOWS: k.MOD_META,
            pk.MOD_COMMAND: k.MOD_CTRL,
            pk.MOD_OPTION: k.MOD_META,
            }
        cls.to_keycode = {
            pk.APOSTROPHE: k.QUOTE,
            pk.BRACKETLEFT: k.LEFTBRACKET,
            pk.BRACKETRIGHT: k.RIGHTBRACKET,
            pk.DOUBLEQUOTE: k.QUOTEDBL,
            pk.ENTER: k.KP_ENTER,
            pk.EQUAL: k.EQUALS,
            pk.EXCLAMATION: k.EXCLAIM,
            pk.MOD_CAPSLOCK: k.CAPSLOCK,
            pk.MOD_NUMLOCK: k.NUMLOCK,
            pk.MOD_SCROLLLOCK: k.SCROLLOCK,
            pk.MOTION_UP: k.UP,
            pk.MOTION_RIGHT: k.RIGHT,
            pk.MOTION_DOWN: k.DOWN,
            pk.MOTION_LEFT: k.LEFT,
            pk.MOTION_NEXT_WORD: None,
            pk.MOTION_PREVIOUS_WORD: None,
            pk.MOTION_BEGINNING_OF_LINE: k.HOME,
            pk.MOTION_END_OF_LINE: k.END,
            pk.MOTION_NEXT_PAGE: k.PAGEDOWN,
            pk.MOTION_PREVIOUS_PAGE: k.PAGEUP,
            pk.MOTION_BEGINNING_OF_FILE: k.HOME,
            pk.MOTION_END_OF_FILE: k.END,
            pk.MOTION_BACKSPACE: k.BACKSPACE,
            pk.MOTION_DELETE: k.DELETE,
            pk.NUM_ADD: k.KP_PLUS,
            pk.NUM_DECIMAL: k.KP_PERIOD,
            pk.PARENLEFT: k.LEFTPAREN,
            pk.PARENRIGHT: k.RIGHTPAREN,
            }
        pkdir = set([name for name in dir(pk) if name == name.upper()])
        kdir = set([name for name in dir(k) if name == name.upper()])
        both = pkdir.intersection(kdir)
        for key in both:
            cls.to_keycode[getattr(pk, key)] = getattr(k, key)
        remaining = pkdir - both
        for key in set(remaining):
            for pk_prefix, k_prefix in [("NUM_", "KP_"), ("NUM_", "KP"), ("_","K")]:
                if key.startswith(pk_prefix):
                    target = k_prefix + key[len(pk_prefix):]
                    if target in kdir:
                        cls.to_keycode[getattr(pk, key)] = getattr(k, target)
                        remaining.remove(key)
                        break
    
    def convert_keycode(self, pyglet_keycode):
        return self.to_keycode.get(pyglet_keycode, None)
        
    ########## Event functions
    
    def post_event(self, event, *args):
        pyglet.app.platform_event_loop.post_event(self, event, *args)
    
    ########## Timer functions
    
    def schedule_once(self, callback, seconds):
        pyglet.clock.schedule_once(callback, seconds)
    
    def unschedule(self, callback):
        pyglet.clock.unschedule(callback)
    
    ########## Drawing functions
    
    def draw_text(self, text, font, x=0, y=0, bold=False, italic=False, color=None, anchor_x='left', anchor_y='bottom'):
        if color is None:
            color = (255, 255, 255, 255)
        label = pyglet.text.Label(text,
                                  font_name=font.name,
                                  font_size=font.size,
                                  bold=bold, italic=italic,
                                  color=color,
                                  x=x, y=y,
                                  anchor_x=anchor_x, anchor_y=anchor_y)
        label.draw()
    
    def draw_markup(self, markup, font, x=0, y=0, color=None, anchor_x='left', anchor_y='bottom', width=0):
        if color is None:
            color = (255, 255, 255, 255)
        replacements = (
            ("<b>", "{bold True}"),
            ("</b>", "{bold False}"),
            ("<i>", "{italic True}"),
            ("</i>", "{italic False}"),
            ("<u>", "{underline %s}" % str(color)),
            ("</u>", "{underline (0,0,0,0)}"),
            ("<center>", "{align center}"),
            ("</center>", "{align left}"),
            ("\n", "{}\n"),
            )
        for s, r in replacements:
            markup = markup.replace(s, r)
        text = "{font_name '%s'}{font_size %s}{color %s}" % (font.name, font.size, str(color)) + markup
        document = pyglet.text.decode_attributed(text)
        label = pyglet.text.DocumentLabel(document, multiline=True,
                                          x=x, y=y, width=width,
                                          anchor_x=anchor_x, anchor_y=anchor_y)
        label.draw()
    
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
        pyglet.graphics.draw(4, GL_QUADS, ('v2i', verts), ('c4B', background_color*4))
        pyglet.graphics.draw(4, GL_LINE_LOOP, ('v2i', verts), ('c4B', border_color*4))


PygletMainWindow.register_event_type('on_status_update')

class PygletFontInfo(FontInfo):
    def calc_height(self):
        font = pyglet.font.load(self.name, self.size)
        self.height = font.ascent - font.descent
