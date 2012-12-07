import os, sys, glob, time
import ui.keycodes as k


class VerticalMenuController(object):
    def __init__(self, layout, config):
        self.layout = layout
        self.config = config
        self.search_string = ""
        self.last_keypress = time.time()
        self.rotate_delay = 1.0 # number of seconds delay to rotate letters using phone keypad text entry
        self.rotate_letter = ""
        self.rotate_string = ""
    
    def get_markup(self):
        return u"<b>\u21e7</b> Up    <b>\u21e9</b> Down    <b>\u21e8</b> Select    <b>\u21e6</b> Previous Menu    <span color='red'><b>\u25cf</b></span> Audio Select    <span color='green'><b>\u25cf</b></span> Subtitle Select    <span color='yellow'><b>\u25cf</b></span> Mark as Favorite    <span color='blue'><b>\u25cf</b></span> Search"

    def process_key_press(self, keycode, modifiers):
        # First, check arrow keys for menu motion
        delta = 0
        if keycode == k.UP:
            delta = -1
        elif keycode == k.PAGEUP:
            delta = -self.layout.menu_renderer.get_page_scroll_unit()
        elif keycode == k.DOWN:
            delta = 1
        elif keycode == k.PAGEDOWN:
            delta = self.layout.menu_renderer.get_page_scroll_unit()
        elif keycode == k.HOME:
            delta = -1000000
        elif keycode == k.END:
            delta = 1000000
        if delta != 0:
            menu = self.layout.get_menu()
            menu.move_cursor(delta)
            return True
        
        if keycode == k.RIGHT or keycode == k.KP_ENTER or keycode == k.RETURN:
            self.process_select()
        elif keycode == k.LEFT:
            self.process_back()
        elif keycode == k.BACKSPACE:
            self.process_backspace()
        elif keycode == k.ESCAPE:
            self.process_quit()
        elif keycode == k.F11:
            self.process_edit('edit_metadata')
        elif keycode == k.F1:
            self.process_audio()
        elif keycode == k.F2:
            self.process_subtitle()
        elif keycode == k.LEFTBRACKET:
            self.layout.window.refresh()
        elif (keycode == k.K8 and modifiers & k.MOD_SHIFT) or keycode == k.F3:
            self.process_star()
        elif keycode == k.F4:
            self.start_search()
        else:
            self.process_search(keycode)
    
    def process_select(self):
        submenu_found = self.layout.select_child_menu()
        if not submenu_found:
            menu = self.layout.get_menu()
            selected = menu.get_selected_item()
            selected.do_action(config=self.config)
            if self.layout.in_sub_menu():
                self.layout.pop_root()
                self.layout.refresh()
    
    def process_edit(self, edit_type):
        menu = self.layout.get_menu()
        selected = menu.get_selected_item()
        new_root = selected.do_create_edit_menu(config=self.config, edit_type=edit_type)
        if new_root is not None:
            self.layout.push_root(new_root)
    
    def process_audio(self):
        menu = self.layout.get_menu()
        selected = menu.get_selected_item()
        selected.do_audio(config=self.config)
    
    def process_subtitle(self):
        menu = self.layout.get_menu()
        selected = menu.get_selected_item()
        selected.do_subtitle(config=self.config)
    
    def process_star(self):
        menu = self.layout.get_menu()
        selected = menu.get_selected_item()
        selected.do_star(config=self.config)
    
    def in_search(self):
        menu = self.layout.get_menu()
        populator = menu.populate_children
        return hasattr(populator, "set_search_text")
     
    def start_search(self):
        if self.in_search():
            return
        menu = self.layout.get_menu()
        populator = menu.populate_children
        if populator is not None and hasattr(populator, "get_search_populator"):
            self.search_string = ""
            search_populator = populator.get_search_populator(self.search_string)
            self.layout.push_root(menu.create_root(search_populator))
            self.last_keypress = time.time()
            self.rotate_letter = ""
            self.rotate_string = ""
    
    rotate_map = {
        '2': "abc2",
        '3': "def3",
        '4': "ghi4",
        '5': "jkl5",
        '6': "mno6",
        '7': "pqrs7",
        '8': "tuv8",
        '9': "wxyz9",
        '0': " 0",
        }
    
    def process_search(self, keycode):
        menu = self.layout.get_menu()
        populator = menu.populate_children
        if not hasattr(populator, "set_search_text"):
            return
        
        rotate = False
        if keycode == k.K1:
            keycode = ord('1')
        elif (keycode >= k.K2 and keycode <= k.K9) or keycode == k.K0:
            keycode = keycode - k.K0 + ord('0')
            rotate = True
        elif keycode < k.SPACE or keycode > 255:
            return
        c = chr(keycode)
        
        # For remotes with phone keypad-style letters, rotate through the
        # letters when the corresponding numbers are picked
        if rotate:
            timestamp = time.time()
            if c == self.rotate_letter and timestamp < self.last_keypress + self.rotate_delay:
                s = self.rotate_string
                self.rotate_string = s[1:] + s[0]
            else:
                self.rotate_letter = c
                self.rotate_string = self.rotate_map[c]
                c = self.rotate_string[0]
                rotate = False
        
        if rotate:
            self.search_string = self.search_string[0:-1] + self.rotate_string[0]
        else:
            self.search_string += c
            
        populator.set_search_text(self.search_string)
        menu.needs_refresh()
        self.layout.refresh()
        self.last_keypress = time.time()
    
    def process_backspace(self):
        if self.in_search():
            self.search_string = self.search_string[0:-1]
            menu = self.layout.get_menu()
            populator = menu.populate_children
            populator.set_search_text(self.search_string)
            menu.needs_refresh()
            self.layout.refresh()
        else:
            self.process_back()

    def process_back(self):
        self.layout.select_parent_menu()

    def process_quit(self):
        try:
            self.layout.pop_root()
        except IndexError:
            self.layout.window.quit()
