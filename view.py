import os, sys, glob
import pyglet

from controller import *


class AbstractLayout(object):
    def __init__(self, window, config):
        self.window = window
        self.config = config
        self.compute_params()
        self.root = None
        self.hierarchy = []
        self.controller = None
    
    def compute_params(self):
        self.width, self.height = self.window.get_size()
        print self.width
        print self.height
    
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
    
    def draw(self, menu):
        pass


class FontSet(object):
    def __init__(self, config):
        self.name = config.get_font_name()
        self.size = config.get_font_size()
        self.selected_size = config.get_selected_font_size()


class MenuDetail2ColumnLayout(AbstractLayout):
    def __init__(self, window, config):
        AbstractLayout.__init__(self, window, config)
        self.controller = VerticalMenuController(self, config)
        self.fonts = FontSet(config)
        self.compute_layout()
        self.title_renderer = config.get_title_renderer(window, self.title_box, self.fonts)
        self.menu_renderer = config.get_menu_renderer(window, self.menu_box, self.fonts)
        self.detail_renderer = config.get_detail_renderer(window, self.detail_box, self.fonts)
    
    def compute_layout(self):
        self.title_height = self.fonts.size + 10
        self.menu_width = self.width/3
        self.center = (self.height - self.title_height)/2
        self.items_in_half = (self.center - self.fonts.selected_size) / self.fonts.size
        self.title_box = (0, self.height - self.title_height + 1, self.width, self.title_height)
        self.menu_box = (0, 0, self.menu_width, self.height - self.title_height)
        self.detail_box = (self.menu_width, 0, self.width - self.menu_width, self.height - self.title_height)
    
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
        x = self.x + 30
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
            x += 30
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
        
    def draw(self, menu):
        item = menu.get_selected_item()
        m = item.get_metadata(self)
        if 'special' in m:
            self.draw_special(item, m)
        else:
            self.draw_media(item, m)
    
    def draw_special(self, item, m):
        if 'image' in m:
            image = self.artwork_loader.get_image(m['image'])
            image.blit(self.x, self.h - image.height, 0)
    
    def draw_media(self, item, m):
        id = m['imdb_id']
        image = self.artwork_loader.get_poster(id)
        image.blit(self.x, self.h - image.height, 0)
        if id not in self.batch_cache:
            batch = pyglet.graphics.Batch()
            genres = u", ".join(m['genres'])
            directors = u", ".join(m['directors'])
            for a in m['producers']:
                print repr(a), type(a)
            print m['producers']
            producers = u", ".join(m['producers'][0:3])
            writers = u", ".join(m['writers'])
            actors = u", ".join(m['actors'])
            music = u", ".join(m['music'])
            title = m['title']
            if m['year']:
                title += u" (%s)" % m['year']
            text = u"""<b>%s</b>
<br>
<br><b>Rated:</b> %s
<br><b>Released:</b> %s
<br><b>Genre:</b> %s
<br><b>Directed by:</b> %s
<br><b>Produced by:</b> %s
<br><b>Written by:</b> %s
<br><b>Music by:</b> %s
<br><b>Actors:</b> %s
<br><b>Runtime:</b> %s
<br><b>Rating:</b> %s/10
<br>
<br><b>Plot:</b> %s""" % (title, m['mpaa'],
                          m['released'], genres, directors, producers,
                          writers, music, actors, m['runtime'],
                          m['rating'], m['description'])
            text = "<font face='%s' size='%s' color='rgb(255,255,255)'>%s</font>" % (self.fonts.name, self.fonts.size, text)
            text = "<font face='%s' size='%s' color='#FFFFFF'>%s</font>" % (self.fonts.name, self.fonts.size, text)
#        label = pyglet.text.Label(text,
#                                  font_name=self.fonts.name,
#                                  font_size=self.fonts.size,
            label = pyglet.text.HTMLLabel(text,
                                          x=self.x + image.width + 10, y=self.h,
                                          anchor_x='left', anchor_y='top',
                                          width=self.w - image.width - 10, multiline=True,
                                          batch=batch)
            self.batch_cache[id] = batch
        self.batch_cache[id].draw()

