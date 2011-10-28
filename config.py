import os, sys, glob
import pyglet

from view import *
from model import Menu
from mplayer import MovieParser


class RootMenu(Menu):
    def __init__(self, config):
        Menu.__init__(self, "Dinoteeth Media Launcher", config)
        self.movies = Menu("Movies", config)
        self.tv = Menu("TV", config)
        self.photos = Menu("Photos", config)
        self.games = Menu("Games", config)
        self.paused = Menu("Paused...", config)
        for item in [self.movies, self.tv, self.photos, self.games, self.paused]:
            self.add_item(item)
        for i in range(50):
            self.tv.add_item(Menu("Entry #%d" % i, self.config))
    
    def parse_dir(self, path):
        print path
        MovieParser.add_videos_in_path(self.movies, self.config, path)
        

class Config(object):
    def __init__(self, args):
        self.layout = None
        self.root = None
        self.default_poster = None
        self.default_mplayer_opts = ["-novm", "-fs", "-utf8"]
        # Use SSA/ASS rendering to enable italics, bold, etc
        self.default_mplayer_opts.extend(["-ass", "-ass-color", "ffffff00", "-ass-font-scale", "1.4"])
        
        self.parse_args(args)
    
    def parse_args(self, args):
        self.root = RootMenu(self)
        if len(args) > 1:
            path = args[1]
        elif os.path.exists("/remote/media2/movies"):
            path = "/remote/media2/movies"
        else:
            path = None
        if path:
            self.root.parse_dir(path)
    
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

    def shell_escape_path(self, path):
        escape_chars = [' ', '&', '(', ')']
        escaped_path = path
        for c in escape_chars: escaped_path = escaped_path.replace(c, "\\"+c)
        return escaped_path

    def get_mplayer_opts(self, path):
        opts = self.default_mplayer_opts[:]
        root, ext = os.path.splitext(path)
        subtitle = root + ".sub"
        if not os.path.exists(subtitle):
            if path.endswith(".mp4"):
                # Assuming that .mp4 files are made by me and have subtitles
                opts.extend(["-slang", "eng"])
            else:
                # If there are no subtitles, force closed captioning
                opts.extend(["-subcc", "1"])
        else:
            # use -noautosub to stop subtitles from being displayed
            #opts.append("-noautosub")
            pass
        return opts

def setup(args):
    return Config(args)
