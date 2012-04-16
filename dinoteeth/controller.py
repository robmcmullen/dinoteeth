import os, sys, glob
import pyglet


class VerticalMenuController(object):
    def __init__(self, layout, config):
        self.layout = layout
        self.config = config

    def process_motion(self, motion):
        menu = self.layout.get_menu()
        k = pyglet.window.key
        
        delta = 0
        if motion == k.MOTION_UP:
            delta = -1
        elif motion == k.MOTION_PREVIOUS_PAGE:
            delta = -self.layout.menu_renderer.get_page_scroll_unit()
        elif motion == k.MOTION_DOWN:
            delta = 1
        elif motion == k.MOTION_NEXT_PAGE:
            delta = self.layout.menu_renderer.get_page_scroll_unit()
        elif motion == k.MOTION_BEGINNING_OF_LINE or motion == k.MOTION_BEGINNING_OF_FILE:
            delta = -1000000
        elif motion == k.MOTION_END_OF_LINE or motion == k.MOTION_END_OF_FILE:
            delta = 1000000
        
        menu.move_cursor(delta)
    
    def process_key_press(self, symbol, modifiers):
        k = pyglet.window.key
        if symbol == k.RIGHT or symbol == k.ENTER or symbol == k.RETURN:
            self.process_select()
        elif symbol == k.LEFT or symbol == k.BACKSPACE:
            self.process_back()
        elif symbol == k.Q or symbol == k.ESCAPE:
            self.process_quit()
        elif symbol == k.E:
            self.process_edit()
        elif symbol == k.A:
            self.process_audio()
        elif symbol == k.S:
            self.process_subtitle()
        elif symbol == k.R:
            self.layout.window.refresh()
    
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
    
    def process_back(self):
        self.layout.select_parent_menu()

    def process_quit(self):
        self.config.do_shutdown_tasks()
        pyglet.app.exit()
