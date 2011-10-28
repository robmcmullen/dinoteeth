import os, sys, glob
import pyglet


class Menu(object):
    def __init__(self, title, config, image=None):
        self.title = title
        self.config = config
        if image is None:
            self.detail_image = self.config.get_default_poster()
        else:
            self.detail_image = image
        
        self.cursor = 0
        self.children = []
        self.playable = False
    
    # Methods regarding the menu itself
    def get_title(self):
        return self.title
    
    def get_detail_image(self):
        return self.detail_image
    
    def get_details(self):
        return "Details for %s" % self.title
    
    # Methods regarding the children of the menu
    def add_item(self, item):
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
    
    # Media methods
    def is_playable(self):
        return self.playable
    
    def play(self):
        pass

