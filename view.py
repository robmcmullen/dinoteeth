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
        self.controller = VerticalMenuController(self)
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
    def __init__(self, window, box, fonts):
        self.window = window
        self.x = box[0]
        self.y = box[1]
        self.w = box[2]
        self.h = box[3]
        self.fonts = fonts
        self.compute_params()
        
    def compute_params(self):
        pass


class MenuRenderer(Renderer):
    def get_page_scroll_unit(self):
        return 10


class VerticalMenuRenderer(MenuRenderer):
    def compute_params(self):
        self.center = self.y + self.h/2
        self.items_in_half = (self.center - self.fonts.selected_size) / self.fonts.size
    
    def get_page_scroll_unit(self):
        return self.items_in_half
    
    def draw(self, menu):
        color = (0, 255, 0, 255)
        item = menu.get_selected_item()
        text = item.get_title()
        # Render center item in larger font
        label = pyglet.text.Label(text,
                                  font_name=self.fonts.name,
                                  font_size=self.fonts.selected_size,
                                  color=color, x=self.x + 30, y=self.center,
                                  anchor_x='left', anchor_y='center')
        label.draw()
        
        y = self.center + self.fonts.selected_size
        i = menu.cursor - 1
        limit = max(0, menu.cursor - self.items_in_half)
        while i >= limit:
            item = menu.get_item(i)
            text = item.get_title()
            label = pyglet.text.Label(text,
                              font_name=self.fonts.name,
                              font_size=self.fonts.size,
                              color=color, x=self.x + 30, y=y,
                              anchor_x='left', anchor_y='center')
            label.draw()
            y += self.fonts.size
            i -= 1
            
        y = self.center - self.fonts.selected_size
        i = menu.cursor + 1
        limit = min(menu.num_items() - 1, menu.cursor + self.items_in_half)
        while i <= limit:
            item = menu.get_item(i)
            text = item.get_title()
            label = pyglet.text.Label(text,
                              font_name=self.fonts.name,
                              font_size=self.fonts.size,
                              color=color, x=self.x + 30, y=y,
                              anchor_x='left', anchor_y='center')
            label.draw()
            y -= self.fonts.size
            i += 1


class TitleRenderer(Renderer):
    def draw(self, hierarchy):
        title = []
        for menu in hierarchy:
            title.append(menu.get_title())
        text = " > ".join(title)
        label = pyglet.text.Label(text,
                                  font_name=self.fonts.name,
                                  font_size=self.fonts.size,
                                  x=self.x + self.w/2, y=self.y,
                                  anchor_x='center', anchor_y='bottom')
        label.draw()


class DetailRenderer(Renderer):
    def draw(self, menu):
        item = menu.get_selected_item()
        image = item.get_detail_image()
        image.blit(self.x, self.h - image.height, 0)
        text = item.get_details()
        label = pyglet.text.Label(text,
                                  font_name=self.fonts.name,
                                  font_size=self.fonts.size,
                                  x=self.x + image.width + 10, y=self.h,
                                  anchor_x='left', anchor_y='top')
        label.draw()

