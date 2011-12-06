import os, sys, glob, bisect


class MenuItem(object):
    def __init__(self, title, enabled=True, action=None, populate=None, media=None):
        self.title = title
        self.enabled = enabled
        self.action = action
        self.populate = populate
        self.media = media
        self.populated = False
        self.cursor = 0
        self.children = []
    
    def __cmp__(self, other):
        return cmp(self.title, other.title)
    
    def add(self, subitem):
        self.children.append(subitem)
    
    def pprint(self, level=""):
        print "%s%s" % (level, self.title)
        for child in self.children:
            child.pprint(level + "  ")
    
    def do_action(self):
        print "action!"
        self.do_populate()
        if self.action:
            self.action()
    
    def do_populate(self):
        if not self.populated:
            if self.populate:
                print "populating!"
                hierarchy = self.populate()
                self.add_hierarchy(hierarchy)
            self.populated = True
    
    def add_hierarchy(self, guess_parent):
        children = guess_parent.children
        prev_guess = None
        for guess in children:
            if guess.children:
                subitem = MenuItem(guess.in_context_title, None)
                self.add(subitem)
                subitem.add_hierarchy(guess)
            else:
                for item in guess.get_items(prev_guess):
                    subitem = MenuItem(item, None)
                    self.add(subitem)
            prev_guess = guess

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
    
    def get_media_object(self):
        return self.media

class Toggle(MenuItem):
    def __init__(self, title, state=False):
        MenuItem.__init__(self, title)
        self.state = state
        self.radio_group = None
        
    def set_radio_group(self, radio_group):
        self.radio_group = radio_group
    
    def do_action(self):
        if self.enabled:
            if self.radio_group:
                self.do_action_radio()
            else:
                self.do_action_toggle()
    
    def do_action_toggle(self, state=None):
        if state is not None:
            self.state = state
        else:
            self.state = not self.state
    
    def do_action_radio(self):
        for toggle in self.radio_group:
            toggle.do_action_toggle(False)
        self.do_action_toggle(True)
