import os, sys, glob
import pyglet


class MenuDetail(object):
    def __init__(self, title, image=None):
        self.title = title
        self.detail_image = image
        self.playable = False
    
    # Methods regarding the menu itself
    def get_title(self):
        return self.title
    
    def get_detail_image(self):
        return self.detail_image
    
    def get_description(self):
        return "Description for %s" % self.title
    
    # Media methods
    def is_playable(self):
        return self.playable
    
    def play(self, conf):
        pass

class Menu(object):
    def __init__(self, string_or_detail):
        if isinstance(string_or_detail, str):
            self.detail = MenuDetail(string_or_detail)
        else:
            self.detail = string_or_detail
        
        self.cursor = 0
        self.children = []
    
    def __cmp__(self, other):
        return cmp(self.detail.get_title(), other.detail.get_title())
    
    # Proxy methods to the MenuDetail for the menu item itself
    def get_title(self):
        return self.detail.get_title()
    
    def get_detail_image(self):
        return self.detail.get_detail_image()
    
    def get_description(self):
        return self.detail.get_description()
    
    # Methods regarding the children of the menu
    def add_item(self, item):
        if not isinstance(item, Menu):
            raise RuntimeError("add_item requires a Menu object (not MenuDetail)")
        self.children.append(item)
    
    def sort_items(self):
        self.children = sorted(self.children)
    
    def get_item(self, i):
        return self.children[i]
    
    def get_selected_item(self):
        return self.children[self.cursor]
        
    def get_items(self):
        return self.children
    
    def num_items(self):
        return len(self.children)
    
    def has_items(self):
        return bool(self.children)
    
    def move_cursor(self, delta):
        self.cursor += delta
        if self.cursor < 0:
            self.cursor = 0
        elif self.cursor >= self.num_items():
            self.cursor = self.num_items() - 1
