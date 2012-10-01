import os, sys, glob
import ui.keycodes as k


class VerticalMenuController(object):
    def __init__(self, layout, config):
        self.layout = layout
        self.config = config

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
        elif keycode == k.LEFT or keycode == k.BACKSPACE:
            self.process_back()
        elif keycode == k.Q or keycode == k.ESCAPE:
            self.process_quit()
        elif keycode == k.E:
            self.process_edit()
        elif keycode == k.A:
            self.process_audio()
        elif keycode == k.S:
            self.process_subtitle()
        elif keycode == k.R:
            self.layout.window.refresh()
        elif keycode == k.K8 and modifiers & k.MOD_SHIFT:
            self.process_star()
    
    def process_select(self):
        submenu_found = self.layout.select_child_menu()
        if not submenu_found:
            menu = self.layout.get_menu()
            selected = menu.get_selected_item()
            selected.do_action(config=self.config)
            if self.layout.in_sub_menu():
                self.layout.pop_root()
                self.layout.refresh()
    
    def process_edit(self):
        menu = self.layout.get_menu()
        selected = menu.get_selected_item()
        new_root = selected.do_create_edit_menu(config=self.config)
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
    
    def process_back(self):
        self.layout.select_parent_menu()

    def process_quit(self):
        try:
            self.layout.pop_root()
        except IndexError:
            self.layout.window.quit()
