import os, sys, glob, time, bisect, logging

from updates import UpdateManager
from utils import DBFacade
import settings

log = logging.getLogger("dinoteeth.model")


class MenuItem(object):
    refresh_time = time.time()
    
    def __init__(self, title, enabled=True, action=None, populate_children=None, media=None, metadata=None, **kwargs):
        self.title = title
        self.enabled = enabled
        self.action = action
        self.populate_children = populate_children
        self.on_selected_item = None
        self.media = media
        self.parent = None
        self.metadata = metadata
        self.populated = 0
        self.cursor = 0
        self.children = []
    
    @classmethod
    def create_root(cls, populator):
        root = MenuItem(populator.root_title, populate_children=populator)
        return root
    
    @classmethod
    def needs_refresh(cls):
        cls.refresh_time = time.time()
    
    def __cmp__(self, other):
        return cmp(self.title, other.title)
    
    def add(self, subitem):
        self.children.append(subitem)
        subitem.parent = self
    
    def pprint(self, level=""):
        print "%s%s" % (level, self.title)
        for child in self.children:
            child.pprint(level + "  ")
    
    def do_on_selected_item(self, **kwargs):
        if self.on_selected_item:
            print "on_selected_item!"
            self.on_selected_item(**kwargs)
    
    def do_action(self, **kwargs):
        if self.enabled:
            print "action!"
            self.do_populate()
            if self.action:
                self.action(**kwargs)
    
    def do_audio(self, **kwargs):
        print "audio!"
        try:
            media_file = self.metadata['media_file']
        except KeyError:
            return
        media_file.scan.next_audio()
    
    def do_subtitle(self, **kwargs):
        print "subtitle!"
        try:
            media_file = self.metadata['media_file']
        except KeyError:
            return
        media_file.scan.next_subtitle(media_file.pathname)
    
    def do_star(self, **kwargs):
        if self.metadata and 'mmdb' in self.metadata:
            base_metadata = self.metadata['mmdb']
            base_metadata.starred = not base_metadata.starred
            if base_metadata.starred:
                log.debug("starred %s" % base_metadata.id)
            else:
                log.debug("unstarred %s" % base_metadata.id)
            DBFacade.commit()
    
    def do_stop(self, **kwargs):
        try:
            media_file = self.metadata['media_file']
        except KeyError:
            return
        media_file.scan.set_last_position()
        DBFacade.commit()
    
    def do_populate(self):
        if self.populated < self.__class__.refresh_time:
            if self.populate_children:
                # root title may have changed
                if hasattr(self.populate_children, "root_title"):
                    self.title = self.populate_children.root_title
                
                data = self.get_cursor_match_data()
                self.children = []
                print "populating children!"
                for child in self.populate_children(self):
                    self.add(child)
                if data is not None:
                    self.set_cursor_from_match_data(data)
            self.populated = time.time()
    
    def get_cursor_match_data(self):
        if len(self.children) == 0:
            return None
        current_cursor = self.cursor
        current_title = self.children[current_cursor].title
        return (current_cursor, current_title)
    
    def set_cursor_from_match_data(self, data):
        # Attempt to match cursor position by title
        current_cursor, current_title = data
        self.cursor = None
        for i, child in enumerate(self.children):
            if child.title == current_title:
                print "Found cursor position at %s" % current_title.encode('utf8')
                self.cursor = i
                break
        
        # Fallback to original cursor position if title was removed
        if self.cursor is None:
            print "Fallback to original cursor position"
            self.cursor = current_cursor
            if self.cursor >= len(self.children):
                self.cursor = len(self.children) - 1
            if self.cursor < 0:
                self.cursor = 0
    
    def do_repopulate(self):
        """Refresh this menu and attempt to keep the cursor on the same item
        even if the new menu is re-sorted
        """
        if not self.populate_children:
            print "can't refresh static menu"
            return
        print "refreshing menu"
        data = self.get_cursor_match_data()
        self.populated = 0
        self.do_populate()
        if data is not None:
            self.set_cursor_from_match_data(data)

    def do_create_edit_menu(self, **kwargs):
        if self.enabled and 'edit_type' in kwargs:
            edit_type = kwargs['edit_type']
            print "edit type: %s" % edit_type
            if self.metadata and edit_type in self.metadata:
                populator = self.metadata[edit_type]
                new_root = self.create_root(populator)
                return new_root
    
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
        if self.num_items() > 0:
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
            log.debug(u" ".join(unicode(s) for s in [title, populator]))
            items.append((title, populator))
        if self.autosort:
            items.sort()
        for title, populator in items:
            item = MenuItem(title, populate_children=populator)
            if populator is None:
                item.enabled = False
            if hasattr(populator, 'play'):
                item.action=populator.play
            if hasattr(populator, 'get_metadata'):
                item.metadata = populator.get_metadata()
            if hasattr(populator, 'on_selected_item'):
                item.on_selected_item = populator.on_selected_item
            yield item
    
    def iter_create(self):
        return []
    
    def iter_image_path(self):
        return []
    
    def get_thumbnail(self, window, imgpath):
        try:
            thumb_image = window.get_thumbnail_image(imgpath)
        except Exception, e:
            log.debug("Skipping failed thumbnail %s: %s" % (imgpath, e))
            return None
        if not thumb_image.is_valid():
            # Thumbnail will be created in background thread and
            # displayed the next time the screen is drawn
            UpdateManager.create_thumbnail(imgpath)
        return thumb_image
    
    def get_mosaic_size(self):
        return 100, 140

    def thumbnail_mosaic_all_at_once(self, window, x, y, w, h):
        nominal_x, nominal_y = self.get_mosaic_size()
        min_x = x
        max_x = x + w
        min_y = y
        y = y + h
        for imgpath in self.iter_image_path():
            thumb_image = self.get_thumbnail(window, imgpath)
            if thumb_image is None:
                continue
            if x + nominal_x > max_x:
                x = min_x
                y -= nominal_y
            if y < min_y:
                break
            window.blit(thumb_image, x + (nominal_x - thumb_image.width) / 2, y - nominal_y + (nominal_y - thumb_image.height) / 2)
            x += nominal_x

    def thumbnail_mosaic_incremental(self, window, x, y, w, h):
        print "thumbnail_mosaic_incremental"
        iterator = self.thumbnail_mosaic_iterator(window, x, y, w, h)
        window.schedule_draw_iterator(iterator)
    
    def thumbnail_mosaic(self, window, x, y, w, h):
        if not settings.delayed_rendering:
            self.thumbnail_mosaic_all_at_once(window, x, y, w, h)
        else:
            self.thumbnail_mosaic_incremental(window, x, y, w, h)
    
    draw_rows = False
    
    def thumbnail_mosaic_iterator(self, window, x, y, w, h):
        print "thumbnail_mosaic_iterator: start"
        window.clear_rect(x, y, w, h)
        nominal_x, nominal_y = self.get_mosaic_size()
        min_x = x
        max_x = x + w
        min_y = y
        y = y + h
        for imgpath in self.iter_image_path():
            print "thumbnail_mosaic_iterator: in loop"
            thumb_image = self.get_thumbnail(window, imgpath)
            if thumb_image is None:
                continue
            print imgpath
            if x + nominal_x > max_x:
                x = min_x
                y -= nominal_y
                if self.draw_rows:
                    yield True
            if y - nominal_y < min_y:
                yield True
                raise StopIteration
            window.blit(thumb_image, x + (nominal_x - thumb_image.width) / 2, y - nominal_y + (nominal_y - thumb_image.height) / 2)
            x += nominal_x
            if not self.draw_rows:
                yield True
