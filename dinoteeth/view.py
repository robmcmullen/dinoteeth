import os, sys, glob, time, random, Queue

from controller import *
from metadata import MetadataLoader

class MenuEmptyError(RuntimeError):
    pass

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
        Box is (x,y,w,h) where the origin is the lower left corner
        """
        self.width, self.height = self.window.get_size()
        self.box = (margins[3], margins[2],
                    self.width - margins[3] - margins[1], 
                    self.height - margins[2] - margins[0])
#        print self.box
    
    def set_root(self, root):
        self.root = root
        self.hierarchy = [root]
        root.activate_menu()
    
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
            return False
        self.hierarchy.append(menu)
        return True
            
    def get_controller(self):
        return self.controller
    
    def refresh(self):
        self.refresh_menu()
    
    def refresh_menu(self):
        self.config.refresh_database()
        menu = self.get_menu()
        menu.do_repopulate()
    
    def draw(self, menu):
        pass


class MenuDetail2ColumnLayout(AbstractLayout):
    def __init__(self, window, margins, config, factory):
        AbstractLayout.__init__(self, window, margins, config)
        self.controller = VerticalMenuController(self, config)
        self.compute_layout()
        self.title_renderer = factory.get_title_renderer(window, self.title_box, config)
        self.menu_renderer = factory.get_menu_renderer(window, self.menu_box, config)
        self.detail_renderer = factory.get_detail_renderer(window, self.detail_box, config)
        self.status_renderer = SimpleStatusRenderer(window, self.status_box, config)
        self.footer_renderer = FooterRenderer(window, self.footer_box, config)
    
    def compute_layout(self):
        x = self.box[0]
        y = self.box[1]
        w = self.box[2]
        h = self.box[3]
        title_h = self.window.font.height + 10
        menu_w = w/3
        footer_h = self.window.font.height + 10
        
        main_y = y + footer_h
        main_h = h - footer_h - title_h
        self.title_box = (x, y + h - title_h + 1, w, title_h)
        self.menu_box = (x, main_y, menu_w - 10, main_h)
        self.detail_box = (x + menu_w, main_y, w - menu_w - x, main_h)
        self.status_box = (menu_w + 10, main_y + 10, w - menu_w - 20, title_h + 20)
        self.footer_box = (-1, -1, self.width + 2, footer_h + y)
    
    def draw(self):
        self.window.clear_draw_iterator()
        self.title_renderer.draw(self.hierarchy)
        while True:
            try:
                menu = self.get_menu()
                self.menu_renderer.draw(menu)
                self.detail_renderer.draw(menu)
                self.status_renderer.draw()
                break
            except MenuEmptyError:
                if self.select_parent_menu():
                    break
        self.footer_renderer.draw(self.controller)


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
    
    def clip(self):
        self.window.clip(self.x, self.y, self.w, self.h)
    
    def unclip(self):
        self.window.unclip()
    
    def clear(self):
        self.window.clear_rect(self.x, self.y, self.w, self.h)


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
        self.items_in_half = int((self.h - (1.5 * self.window.selected_font.height)) / self.window.font.height / 2)
    
    def get_page_scroll_unit(self):
        return self.items_in_half
    
    def draw_item(self, item, y, selected=False):
        text = _(item.title)
        if selected:
            font = self.window.selected_font
            italic = False
            self.window.draw_box(self.x, y - font.height/2, self.w - 1, font.height,
                             (255, 255, 255, 64), (255, 255, 255, 100))
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
        try:
            item = menu.get_selected_item()
        except IndexError:
            raise MenuEmptyError
        self.clear()
        self.clip()
        self.draw_item(item, self.center, True)
        item.do_on_selected_item()
        
        y = self.center + self.window.selected_font.height
        i = menu.cursor - 1
        limit = max(0, menu.cursor - self.items_in_half)
        while i >= limit:
            item = menu.get_item(i)
            self.draw_item(item, y, False)
            y += self.window.font.height
            i -= 1
            
        y = self.center - self.window.selected_font.height
        i = menu.cursor + 1
        limit = min(menu.num_items() - 1, menu.cursor + self.items_in_half)
        while i <= limit:
            item = menu.get_item(i)
            self.draw_item(item, y, False)
            y -= self.window.font.height
            i += 1
        self.unclip()


class TitleRenderer(Renderer):
    def draw(self, hierarchy):
        self.clear()
        title = []
        for menu in hierarchy:
            title.append(menu.title)
        text = _(" > ".join(title))
        self.window.draw_text(text, font=self.window.font,
                                  bold=True, italic=False,
                                  x=self.x + self.w/2, y=self.y,
                                  anchor_x='center', anchor_y='bottom')


class DetailRenderer(Renderer):
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
        elif 'poster_path' in m:
            self.draw_poster(item, m)
    
    def draw_image(self, item, m):
        self.clear()
        image = self.window.get_image(m['image'])
        self.window.blit(image, self.x, self.h - image.height, 0)
    
    def draw_imagegen(self, item, m):
        image_generator = m['imagegen']
        image_generator(self.window, self.x, self.y, self.w, self.h)
    
    def draw_mmdb(self, item, m):
        self.clear()
        metadata = m['mmdb']
        season = m.get('season', None)
        loader = MetadataLoader.get_loader(metadata)
        imgpath = loader.get_poster(metadata, season=season)
        print "draw_mmdb: %s, type=%s" % (imgpath, type(imgpath))
        image = self.window.get_image(imgpath)
        y = self.y + self.h - image.height
        self.window.blit(image, self.x, y, 0)
        
        self.window.draw_markup(metadata.get_markup(m.get('media_file', None)),
                                self.window.detail_font,
                                x=self.x + image.width + 10, y=self.y + self.h,
                                anchor_x='left', anchor_y='top',
                                width=self.w - image.width - 10)
        
        icon_codes = metadata.get_icon_codes(m.get('media_file', None))
        print icon_codes
        x = self.x
        for icon_code in icon_codes:
            imgpath = loader.get_icon(icon_code)
            if imgpath is None:
                continue
            print imgpath
            image = self.window.get_image(imgpath)
            self.window.blit(image, x, y - image.height-10, 0)
            x += image.width + 10

    def draw_imdb_search_result(self, item, m):
        self.clear()
        result = m['imdb_search_result']
        print result
        metadata = m['metadata']
        loader = MetadataLoader.get_loader(metadata)
        imgpath = loader.get_poster(metadata)
        image = self.window.get_image(imgpath)
        self.window.blit(image, self.x, self.h - image.height, 0)
        
        akas = "\n".join([a.replace('::', ' -- ') for a in result.get('akas',[])])
        text = u"""<b>Title:</b> %s
<b>ID:</b> %s
<b>Year:</b> %s
<b>Type:</b> %s

<b>Also known as:</b>
%s
""" % (result['title'], metadata.id, result['year'], result['kind'], akas)

        self.window.draw_markup(text, self.window.detail_font,
                                x=self.x + image.width + 10, y=self.h,
                                anchor_x='left', anchor_y='top',
                                width=self.w - image.width - 10)
    
    def draw_poster(self, item, m):
        self.clear()
        imgpath = m['poster_path']
        image = self.window.get_image(imgpath)
        self.window.blit(image, self.x, self.y + self.h - image.height, 0)


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
                self.last_item = _(item)
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

class FooterRenderer(Renderer):
    def draw(self, controller):
        self.clear()
        text = controller.get_markup()
        self.window.draw_box(self.x, self.y, self.w, self.h,
                             (0,0,0,255), (255, 255, 255, 255))
        if not text:
            return
        self.window.draw_markup(text, self.window.font,
                                x=self.x + 10, y=self.y + self.h - 10 - self.window.font.height / 2,
                                anchor_x='left', anchor_y='center')
