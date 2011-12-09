import os, sys, glob, bisect


class MenuItem(object):
    def __init__(self, title, enabled=True, action=None, populate=None, media=None, theme=None, **kwargs):
        self.title = title
        self.enabled = enabled
        self.action = action
        self.populate = populate
        self.media = media
        self.theme = theme
        self.parent = None
        self.populated = False
        self.cursor = 0
        self.children = []
    
    def __cmp__(self, other):
        return cmp(self.title, other.title)
    
    def add(self, subitem):
        self.children.append(subitem)
        subitem.parent = self
    
    def pprint(self, level=""):
        print "%s%s" % (level, self.title)
        for child in self.children:
            child.pprint(level + "  ")
    
    def get_theme(self):
        item = self
        while item.theme is None:
            item = item.parent
            if item is None:
                raise RuntimeError("Theme not found in menu hierarchy")
        return item.theme
    
    def do_action(self, **kwargs):
        if self.enabled:
            print "action!"
            self.do_populate()
            if self.action:
                self.action(**kwargs)
    
    def do_populate(self):
        if not self.populated:
            if self.populate:
                print "populating!"
                hierarchy = self.populate()
                theme = self.get_theme()
                theme.add_menu_hierarchy(self, hierarchy)
            self.populated = True

    def get_item(self, i):
        self.do_populate()
        return self.children[i]
    
    def get_selected_item(self):
        self.do_populate()
        return self.children[self.cursor]
        
    def get_items(self):
        self.do_populate()
        return self.children
    
    def num_items(self):
        self.do_populate()
        return len(self.children)
    
    def has_items(self):
        self.do_populate()
        return bool(self.children)
    
    def move_cursor(self, delta):
        self.cursor += delta
        if self.cursor < 0:
            self.cursor = 0
        elif self.cursor >= self.num_items():
            self.cursor = self.num_items() - 1
        self.verify_cursor(delta)
    
    def is_selectable(self):
        return self.enabled
    
    def verify_cursor(self, delta):
        """Verify that the cursor isn't over a non-selectable menu item
        
        """
        if delta >= 0:
            delta = 1
        else:
            delta = -1
        first = True
        while not self.children[self.cursor].is_selectable():
            self.cursor += delta
            if self.cursor < 0:
                self.cursor = 0
                
                # bounce the other way if reached the top of the list
                delta = 1
                if not first:
                    break
                first = False
            elif self.cursor >= self.num_items():
                self.cursor = self.num_items() - 1
                
                # bounce the other way if reached the bottom of the list
                delta = -1
                if not first:
                    break
                first = False
            
    def activate_menu(self):
        self.move_cursor(0)
    
    def get_media_object(self):
        return self.media
    
    def is_toggle(self):
        return False

class Toggle(MenuItem):
    def __init__(self, title, state=False, radio=None, index=0, **kwargs):
        MenuItem.__init__(self, title, **kwargs)
        self.state = state
        self.radio_group = radio
        self.index = index
        
    def set_radio_group(self, radio_group):
        self.radio_group = radio_group
    
    def do_action(self, **kwargs):
        if self.enabled:
            if self.radio_group:
                self.do_action_radio()
            else:
                self.do_action_toggle()
            if self.action:
                self.action(index=self.index, **kwargs)
    
    def do_action_toggle(self, state=None):
        if state is not None:
            self.state = state
        else:
            self.state = not self.state
    
    def do_action_radio(self):
        for toggle in self.radio_group:
            toggle.do_action_toggle(False)
        self.do_action_toggle(True)
    
    def initialize_action(self):
        if self.action:
            for toggle in self.radio_group:
                if toggle.state:
                    self.action(index=toggle.index)
                    break
    
    def is_toggle(self):
        return True
