import os, sys, glob, time, random, Queue

from controller import *

class AbstractLayout(object):
    def __init__(self, window, margins, config):
        self.window = window
        self.config = config
        self.compute_params(margins)
        self.root = None
        self.hierarchy = []
        self.stack = []
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
    
    def push_root(self, new_root):
        self.stack.append((self.root, self.hierarchy))
        self.set_root(new_root)
    
    def pop_root(self):
        self.root, self.hierarchy = self.stack.pop()
    
    def in_sub_menu(self):
        return len(self.stack) > 0
    
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


class MenuDetail2ColumnLayout(AbstractLayout):
    def __init__(self, window, margins, config):
        AbstractLayout.__init__(self, window, margins, config)
        self.controller = VerticalMenuController(self, config)
        self.compute_layout()
        self.title_renderer = config.get_title_renderer(window, self.title_box)
        self.menu_renderer = config.get_menu_renderer(window, self.menu_box)
        self.detail_renderer = config.get_detail_renderer(window, self.detail_box)
        self.status_renderer = SimpleStatusRenderer(window, self.status_box, config)
    
    def compute_layout(self):
        self.title_height = self.window.font.size + 10
        self.menu_width = self.box[2]/3
        self.center = (self.box[3] - self.title_height)/2
        self.items_in_half = (self.center - self.window.selected_font.size) / self.window.font.size
        self.title_box = (self.box[0], self.box[3] - self.title_height + 1, self.box[2], self.title_height)
        self.menu_box = (self.box[0], self.box[1], self.menu_width, self.box[3] - self.title_height)
        self.detail_box = (self.menu_width, self.box[1], self.box[2] - self.menu_width, self.box[3] - self.title_height)
        self.status_box = (self.menu_width + 10, self.box[1] + 10, self.box[2] - self.menu_width - 20, self.title_height + 20)
    
    def draw(self):
        self.title_renderer.draw(self.hierarchy)
        menu = self.get_menu()
        self.menu_renderer.draw(menu)
        self.detail_renderer.draw(menu)
        self.status_renderer.draw()


class Renderer(object):
    def __init__(self, window, box, conf):
        self.window = window
        self.x = box[0]
        self.y = box[1]
        self.w = box[2]
        self.h = box[3]
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
        self.items_in_half = (self.center - self.window.selected_font.size) / self.window.font.size
    
    def get_page_scroll_unit(self):
        return self.items_in_half
    
    def draw_item(self, item, y, selected=False):
        text = item.title
        if selected:
            font = self.window.selected_font
            italic = False
        else:
            font = self.window.font
            italic = True
        x = self.x + self.window.font.height
        color = self.get_color(item)
        if item.is_toggle():
            if item.state:
                self.window.draw_text("*", font=font,
                                          bold=False, italic=italic,
                                          color=color,
                                          x=x, y=y,
                                          anchor_x='left', anchor_y='center')
            x += self.window.font.height
        self.window.draw_text(text, font=font,
                                  bold=False, italic=italic,
                                  color=color,
                                  x=x, y=y,
                                  anchor_x='left', anchor_y='center')
    
    def draw(self, menu):
        item = menu.get_selected_item()
        self.draw_item(item, self.center, True)
        
        y = self.center + self.window.selected_font.size
        i = menu.cursor - 1
        limit = max(0, menu.cursor - self.items_in_half)
        while i >= limit:
            item = menu.get_item(i)
            self.draw_item(item, y, False)
            y += self.window.font.size
            i -= 1
            
        y = self.center - self.window.selected_font.size
        i = menu.cursor + 1
        limit = min(menu.num_items() - 1, menu.cursor + self.items_in_half)
        while i <= limit:
            item = menu.get_item(i)
            self.draw_item(item, y, False)
            y -= self.window.font.size
            i += 1


class TitleRenderer(Renderer):
    def draw(self, hierarchy):
        title = []
        for menu in hierarchy:
            title.append(menu.title)
        text = " > ".join(title)
        self.window.draw_text(text, font=self.window.font,
                                  bold=True, italic=False,
                                  x=self.x + self.w/2, y=self.y,
                                  anchor_x='center', anchor_y='bottom')


class DetailRenderer(Renderer):
    def compute_params(self, conf):
        self.artwork_loader = conf.get_artwork_loader()
        
    def draw(self, menu):
        item = menu.get_selected_item()
        m = item.get_metadata(self)
        if m is None:
            return
        if 'image' in m:
            self.draw_image(item, m)
        elif 'imagegen' in m:
            self.draw_imagegen(item, m)
        elif 'mmdb' in m:
            self.draw_mmdb(item, m)
        elif 'imdb_search_result' in m:
            self.draw_imdb_search_result(item, m)
    
    def draw_image(self, item, m):
        image = self.artwork_loader.full_size_loader.get_image(m['image'])
        image.blit(self.x, self.h - image.height, 0)
    
    def draw_imagegen(self, item, m):
        image_generator = m['imagegen']
        image_generator(self.window, self.artwork_loader, self.x, self.y, self.w, self.h)
    
    def draw_mmdb(self, item, m):
        imdb_id = m['mmdb'].id
        season = m.get('season', None)
        key = (imdb_id, season)
        image = self.artwork_loader.get_poster(imdb_id, season)
        image.blit(self.x, self.h - image.height, 0)
        
        self.window.draw_markup(m['mmdb'].get_markup(m.get('media_scan', None)),
                                self.window.detail_font,
                                x=self.x + image.width + 10, y=self.h,
                                anchor_x='left', anchor_y='top',
                                width=self.w - image.width - 10)

    def draw_imdb_search_result(self, item, m):
        result = m['imdb_search_result']
        print result
        imdb_id = result.imdb_id
        image = self.artwork_loader.get_poster(imdb_id, None)
        image.blit(self.x, self.h - image.height, 0)
        
        akas = "\n".join([a.replace('::', ' -- ') for a in result.get('akas',[])])
        text = u"""<b>Title:</b> %s
<b>Year:</b> %s
<b>Type:</b> %s

<b>Also known as:</b>
%s
""" % (result['title'], result['year'], result['kind'], akas)

        self.window.draw_markup(text, self.window.detail_font,
                                x=self.x + image.width + 10, y=self.h,
                                anchor_x='left', anchor_y='top',
                                width=self.w - image.width - 10)

class StatusRenderer(Renderer):
    def draw(self):
        pass

class SimpleStatusRenderer(StatusRenderer):
    def compute_params(self, conf):
        self.last_item = None
        self.expire_time = time.time()
        self.display_interval = 5
    
    def draw(self):
        found = False
        while True:
            try:
                # Pull as many status updates off the queue as there are; only
                # display the most recent update
                item = self.window.status_text.get(False)
                found = True
                self.last_item = item
            except Queue.Empty:
                break
        if found:
            # New item found means resetting the countdown timer back to the
            # maximum
            self.expire_time = time.time() + self.display_interval
            self.window.unschedule(self.window.on_status_change)
            self.window.schedule_once(self.window.on_status_change, self.display_interval)
        else:
            # No items found means that the countdown timer is left as-is
            if self.last_item is None:
                return
            
        if time.time() > self.expire_time:
            # If the countdown timer has expired, no drawing takes place
            self.window.unschedule(self.window.on_status_change)
            return
        #print "status drawing! (%d,%d) %s" % (self.x, self.y, self.last_item)
        self.window.draw_box(self.x, self.y, self.w, self.h,
                             (255, 255, 255, 64), (255, 255, 255, 100))
        self.window.draw_text(self.last_item, font=self.window.font,
                                  bold=False, italic=True, color=(0,0,255,128),
                                  x=self.x + 10, y=self.y + (self.h / 2),
                                  anchor_x='left', anchor_y='center')
