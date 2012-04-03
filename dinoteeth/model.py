import os, sys, glob, bisect, logging

log = logging.getLogger("dinoteeth.model")


class MenuItem(object):
    def __init__(self, title, enabled=True, action=None, populate=None, populate_children=None, media=None, metadata=None, **kwargs):
        self.title = title
        self.enabled = enabled
        self.action = action
        self.populate = populate
        self.populate_children = populate_children
        self.media = media
        self.parent = None
        self.metadata = metadata
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
    
    def do_action(self, **kwargs):
        if self.enabled:
            print "action!"
            self.do_populate()
            if self.action:
                self.action(**kwargs)
    
    def do_audio(self, **kwargs):
        print "audio!"
        if self.metadata and self.metadata['media_scan']:
            media_scan = self.metadata['media_scan']
            media_scan.next_audio()
    
    def do_subtitle(self, **kwargs):
        print "subtitle!"
        if self.metadata and self.metadata['media_scan']:
            media_scan = self.metadata['media_scan']
            media_scan.next_subtitle()
    
    def do_populate(self):
        if not self.populated:
            if self.populate_children:
                print "populating children!"
                for child in self.populate_children(self):
                    self.add(child)
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
    
    def get_metadata(self, renderer):
        """Return a dict that represents the detail to be used by the specified
        renderer
        """
        # Find metadata in parents if not specified in this menu item
        metadata = self.metadata
        parent = self.parent
        while parent and not metadata:
            metadata = parent.metadata
            parent = parent.parent
        
        # Metadata must exist in root menu, or this will return None and
        # probably fail further up the chain.
        return metadata

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


class MenuPopulator(object):
    autosort = False
    
    def __init__(self, config):
        self.config = config
        self.children = []
    
    def __call__(self, parent):
        items = []
        for title, populator in self.iter_create():
            items.append((title, populator))
        if self.autosort:
            items.sort()
        for title, populator in items:
            item = MenuItem(title, populate_children=populator)
            if hasattr(populator, 'play'):
                item.action=populator.play
            if hasattr(populator, 'get_metadata'):
                item.metadata = populator.get_metadata()
            yield item
    
    def iter_create(self):
        raise StopIteration
    
    def iter_image_path(self, artwork_loader):
        raise RuntimeError("abstract method must be overridden in subclass")

    def thumbnail_mosaic(self, artwork_loader, thumbnail_factory, x, y, w, h):
        min_x = x
        max_x = x + w
        min_y = y
        y = y + h
        nominal_x = 100
        nominal_y = 140
        for imgpath in self.iter_image_path(artwork_loader):
            try:
                thumb_image = thumbnail_factory.get_image(imgpath)
            except:
                log.warning("Failed creating thumbnail image for %s" % imgpath)
                continue
            if x + nominal_x > max_x:
                x = min_x
                y -= nominal_y
            if y < min_y:
                break
            thumb_image.blit(x + (nominal_x - thumb_image.width) / 2, y - nominal_y + (nominal_y - thumb_image.height) / 2, 0)
            x += nominal_x
