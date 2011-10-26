import os, sys, glob
import pyglet

from view import *
from controller import *


class Config(object):
    def __init__(self, args):
        self.layout = None
        self.root = None
        self.parse_args(args)
        self.default_poster = None
    
    def parse_args(self, args):
        if len(args) > 1:
            path = args[1]
        elif os.path.exists("/remote/media2/movies"):
            path = "/remote/media2/movies"
        else:
            path = None
        if path:
            self.root = MovieMenu(self, path)
        else:
            self.root = Menu(self)
    
    def get_root(self, window):
        return self.root
    
    def get_layout(self, window):
        return MenuDetail2ColumnLayout(window, self)
    
    def get_font_name(self):
        return "Droid Sans"
    
    def get_font_size(self):
        return 20
    
    def get_selected_font_size(self):
        return 26

    def get_title_renderer(self, window, box, fonts):
        return TitleRenderer(window, box, fonts)

    def get_menu_renderer(self, window, box, fonts):
        return VerticalMenuRenderer(window, box, fonts)

    def get_detail_renderer(self, window, box, fonts):
        return DetailRenderer(window, box, fonts)
    
    def get_default_poster(self):
        if self.default_poster is None:
            self.default_poster = pyglet.image.load("../artwork-not-available.png")
        return self.default_poster
    
    def decode_title_text(self, text):
        return text.replace('_n_',' & ').replace('-s_','\'s ').replace('-t_','\'t ').replace('-m_','\'m ').replace('_',' ')



def setup(args):
    return Config(args)
