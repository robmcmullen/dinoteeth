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
    
    def process_select(self):
        if self.layout.select_child_menu():
            print "child menu found"
        else:
            menu = self.layout.get_menu()
            selected = menu.get_selected_item()
            selected.do_action(config=self.config)
    
    def process_back(self):
        if self.layout.select_parent_menu():
            print "menu found"
        else:
            print "already at root"

    def process_quit(self):
        self.config.save_state()
        pyglet.app.exit()
