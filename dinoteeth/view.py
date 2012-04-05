import os, sys, glob, time
import pyglet
from threading import Thread

USE_OBJGRAPH = False
USE_HEAPY = False

if USE_OBJGRAPH:
    import objgraph
if USE_HEAPY:
    from guppy import hpy
    hp = hpy()

from controller import *
from thumbnail import PygletThumbnailFactory

class ClockTimer(pyglet.event.EventDispatcher):
    def tick(self):
        self.dispatch_event('on_status_update')
ClockTimer.register_event_type('on_status_update')

class ClockThread(Thread):
    def __init__(self, notify_window):
        Thread.__init__(self)
        self._notify_window = notify_window
        self._want_abort = False
        self._ignore = False
        self._ticks_per_second = 10
        self._run = True
        self.start()

    def run(self):
        while True:
            time.sleep(1.0)
            print "Thread awake!"
            self._notify_window.timer.tick()
            if self._want_abort:
                return

    def abort(self):
        # Method for use by main thread to signal an abort
        self._want_abort = 1

class MainWindow(pyglet.window.Window):
    def __init__(self, config, fullscreen=True, width=800, height=600, margins=None):
        if fullscreen:
            super(MainWindow, self).__init__(fullscreen=fullscreen)
        else:
            super(MainWindow, self).__init__(width, height)
        if margins is None:
            margins = (0, 0, 0, 0)
        self.layout = config.get_layout(self, margins)
        root = config.get_root(self)
        self.layout.set_root(root)
        self.controller = self.layout.get_controller()
        if USE_OBJGRAPH:
            objgraph.show_growth()
        if USE_HEAPY:
            print hp.heap()
        self.timer = ClockTimer()
        self.timer.push_handlers(self)
        self.thread = ClockThread(self)
    
    def on_draw(self):
#        print "draw"
        self.clear()
        self.layout.draw()
    
    def refresh(self):
#        print "refresh"
        self.layout.refresh()
        self.flip()
    
    def on_text_motion(self, motion):
        self.controller.process_motion(motion)
        self.flip()
        print "on_text_motion"
        if USE_OBJGRAPH:
            objgraph.show_growth()
        if USE_HEAPY:
            print hp.heap()

    def on_key_press(self, symbol, modifiers):
#        print symbol
        self.controller.process_key_press(symbol, modifiers)
        self.flip()
        print "on_key_press"
        if USE_OBJGRAPH:
            objgraph.show_growth()
        if USE_HEAPY:
            print hp.heap()
    
    def on_status_update(self):
        print "status update from thread!!!"
    
    def stop_threads(self):
        self.thread.abort()


class AbstractLayout(object):
    def __init__(self, window, margins, config):
        self.window = window
        self.config = config
        self.compute_params(margins)
        self.root = None
        self.hierarchy = []
        self.controller = None
    
    def compute_params(self, margins):
        """Compute layout size
        
        Margins are in css order (top, right, bottom, left)
        """
        self.width, self.height = self.window.get_size()
        self.box = (margins[3], margins[2],
                    self.width - margins[3] - margins[1], 
                    self.height - margins[2] - margins[0])
#        print self.box
    
    def set_root(self, root):
        self.root = root
        self.hierarchy = [root]
    
    def get_menu(self):
        return self.hierarchy[-1]
    
    def select_child_menu(self):
        menu = self.get_menu()
        selected = menu.get_selected_item()
        if selected.has_items():
            selected.activate_menu()
            self.hierarchy.append(selected)
            return True
        return False
    
    def select_parent_menu(self):
        menu = self.hierarchy.pop()
        if self.hierarchy:
            return True
        self.hierarchy.append(menu)
        return False
            
    def get_controller(self):
        return self.controller
    
    def refresh(self):
        self.refresh_menu()
    
    def refresh_menu(self):
        menu = self.get_menu()
        menu.do_repopulate()
    
    def draw(self, menu):
        pass


class FontSet(object):
    def __init__(self, config):
        self.name = config.get_font_name()
        self.size = config.get_font_size()
        font = pyglet.font.load(self.name, self.size)
        self.height = font.ascent - font.descent
        self.detail_size = config.get_detail_font_size()
        self.selected_size = config.get_selected_font_size()


class MenuDetail2ColumnLayout(AbstractLayout):
    def __init__(self, window, margins, config):
        AbstractLayout.__init__(self, window, margins, config)
        self.controller = VerticalMenuController(self, config)
        self.fonts = FontSet(config)
        self.compute_layout()
        self.title_renderer = config.get_title_renderer(window, self.title_box, self.fonts)
        self.menu_renderer = config.get_menu_renderer(window, self.menu_box, self.fonts)
        self.detail_renderer = config.get_detail_renderer(window, self.detail_box, self.fonts)
    
    def compute_layout(self):
        self.title_height = self.fonts.size + 10
        self.menu_width = self.box[2]/3
        self.center = (self.box[3] - self.title_height)/2
        self.items_in_half = (self.center - self.fonts.selected_size) / self.fonts.size
        self.title_box = (self.box[0], self.box[3] - self.title_height + 1, self.box[2], self.title_height)
        self.menu_box = (self.box[0], self.box[1], self.menu_width, self.box[3] - self.title_height)
        self.detail_box = (self.menu_width, self.box[1], self.box[2] - self.menu_width, self.box[3] - self.title_height)
    
    def draw(self):
        self.title_renderer.draw(self.hierarchy)
        menu = self.get_menu()
        self.menu_renderer.draw(menu)
        self.detail_renderer.draw(menu)


class Renderer(object):
    def __init__(self, window, box, fonts, conf):
        self.window = window
        self.x = box[0]
        self.y = box[1]
        self.w = box[2]
        self.h = box[3]
        self.fonts = fonts
        self.compute_params(conf)
        
    def compute_params(self, conf):
        pass


class MenuRenderer(Renderer):
    def get_page_scroll_unit(self):
        return 10

    def get_color(self, item):
        color = (0, 255, 0, 255)
        if not item.enabled:
            color = [c/2 for c in color]
        return color

class VerticalMenuRenderer(MenuRenderer):
    def compute_params(self, conf):
        self.center = self.y + self.h/2
        self.items_in_half = (self.center - self.fonts.selected_size) / self.fonts.size
    
    def get_page_scroll_unit(self):
        return self.items_in_half
    
    def draw_item(self, item, y, selected=False):
        text = item.title
        if selected:
            size = self.fonts.selected_size
            italic = False
        else:
            size = self.fonts.size
            italic = True
        x = self.x + self.fonts.height
        color = self.get_color(item)
        if item.is_toggle():
            if item.state:
                label = pyglet.text.Label("*",
                                          font_name=self.fonts.name,
                                          font_size=size,
                                          bold=False, italic=italic,
                                          color=color,
                                          x=x, y=y,
                                          anchor_x='left', anchor_y='center')
                label.draw()
            x += self.fonts.height
        label = pyglet.text.Label(text,
                                  font_name=self.fonts.name,
                                  font_size=size,
                                  bold=False, italic=italic,
                                  color=color,
                                  x=x, y=y,
                                  anchor_x='left', anchor_y='center')
        label.draw()
    
    def draw(self, menu):
        item = menu.get_selected_item()
        self.draw_item(item, self.center, True)
        
        y = self.center + self.fonts.selected_size
        i = menu.cursor - 1
        limit = max(0, menu.cursor - self.items_in_half)
        while i >= limit:
            item = menu.get_item(i)
            self.draw_item(item, y, False)
            y += self.fonts.size
            i -= 1
            
        y = self.center - self.fonts.selected_size
        i = menu.cursor + 1
        limit = min(menu.num_items() - 1, menu.cursor + self.items_in_half)
        while i <= limit:
            item = menu.get_item(i)
            self.draw_item(item, y, False)
            y -= self.fonts.size
            i += 1


class TitleRenderer(Renderer):
    def draw(self, hierarchy):
        title = []
        for menu in hierarchy:
            title.append(menu.title)
        text = " > ".join(title)
        label = pyglet.text.Label(text,
                                  font_name=self.fonts.name,
                                  font_size=self.fonts.size,
                                  bold=True, italic=False,
                                  x=self.x + self.w/2, y=self.y,
                                  anchor_x='center', anchor_y='bottom')
        label.draw()


class DetailRenderer(Renderer):
    def compute_params(self, conf):
        self.artwork_loader = conf.get_artwork_loader()
        self.batch_cache = {}
        self.use_batch = True
        self.thumbs = PygletThumbnailFactory()
        
    def draw(self, menu):
        item = menu.get_selected_item()
        m = item.get_metadata(self)
        if 'image' in m:
            self.draw_image(item, m)
        elif 'imagegen' in m:
            self.draw_imagegen(item, m)
        elif 'mmdb' in m:
            self.draw_mmdb(item, m)
    
    def draw_image(self, item, m):
        image = self.artwork_loader.get_image(m['image'])
        image.blit(self.x, self.h - image.height, 0)
    
    def draw_imagegen(self, item, m):
        image_generator = m['imagegen']
        image_generator(self.artwork_loader, self.thumbs, self.x, self.y, self.w, self.h)
    
    def draw_mmdb(self, item, m):
        imdb_id = m['mmdb'].id
        season = m.get('season', None)
        key = (imdb_id, season)
        image = self.artwork_loader.get_poster(imdb_id, season)
        image.blit(self.x, self.h - image.height, 0)
        
        if not self.batch_cache:
            batch = pyglet.graphics.Batch()
            document = pyglet.text.decode_attributed("")
            self.label = pyglet.text.DocumentLabel(document,
                                          x=self.x + image.width + 10, y=self.h,
                                          anchor_x='left', anchor_y='top',
                                          width=self.w - image.width - 10, multiline=True,
                                          batch=batch)
            self.batch_cache[True] = batch
        
        text = "{font_name '%s'}{font_size %s}{color (255,255,255,255)}" % (self.fonts.name, self.fonts.detail_size) + m['mmdb'].get_pyglet_text(m.get('media_scan', None))
        document = pyglet.text.decode_attributed(text)
        self.label.document = document
        self.batch_cache[True].draw()
