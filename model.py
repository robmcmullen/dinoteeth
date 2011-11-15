import os, sys, glob, bisect


class MenuDetail(object):
    def __init__(self, title, image=None):
        self.title = title
        self.detail_image = image
    
    # Methods regarding the menu itself
    def get_full_title(self):
        return self.title
    
    def get_feature_title(self):
        return self.title
    
    def get_episode_name(self):
        return ""
    
    def get_detail_image(self):
        return self.detail_image
    
    def get_description(self):
        return "Description for %s" % self.title
    
    # Media methods
    def is_playable(self):
        return False
    
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
        try:
            return cmp(self.detail.get_full_title(), other.detail.get_full_title())
        except AttributeError:
            return cmp(unicode(self.detail.get_full_title()), unicode(other.detail.get_full_title()))
    
    # Proxy methods to the MenuDetail for the menu item itself
    def get_full_title(self):
        return self.detail.get_full_title()
    
    def get_feature_title(self):
        return self.detail.get_feature_title()
    
    def get_episode_name(self):
        return ""
    
    def get_detail_image(self):
        return self.detail.get_detail_image()
    
    def get_description(self):
        return self.detail.get_description()
    
    # Methods regarding the children of the menu
    def add_item(self, item):
        if not isinstance(item, Menu):
            raise RuntimeError("add_item requires a Menu object (not MenuDetail)")
        self.children.append(item)
    
    def add_item_by_title_detail(self, detail, submenu_class):
        """Special case: add MediaDetail item using its MovieTitle item and
        sort into sub-menus if necessary
        """
        added = False
        title = detail.get_feature_title()
        print "adding %s" % title
        for item in self.children:
            if title == item.detail.get_feature_title():
                print "found existing title %s" % item.get_feature_title()
                if not item.has_items():
                    # The existing item is not already a submenu, so need
                    # to move the item's details into a submenu...
                    item.add_item(submenu_class(item.detail))
                    # ...  and replace the detail of the current item with
                    # a placeholder detail
                    item.detail = MenuDetail(item.detail.get_feature_title())
                item.add_item(Menu(detail))
                added = True
                break
        if not added:
            self.add_item(Menu(detail))
    
    def sort_items(self):
        self.children = sorted(self.children)
        for item in self.children:
            if item.has_items():
                item.sort_items()
    
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
