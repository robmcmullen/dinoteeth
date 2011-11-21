import os, sys, glob, re
import pyglet
from optparse import OptionParser

from view import *
from model import Menu
from database import DictDatabase
from media import getDetail, guess_media_info

class RootMenu(Menu):
    def __init__(self):
        Menu.__init__(self, "Dinoteeth Media Launcher")
        self.category_order = ["Movies", "TV", "Photos", "Games", "Paused..."]
        self.categories = {}
        self.aliases = {"series": "TV",
                        "episode": "TV",
                        "movie": "Movies",
                        }
        self.db = DictDatabase(self.aliases)
    
    def normalize_category(self, category):
        alias = category.lower()
        if alias in self.aliases:
            category = self.aliases[alias]
        return category
    
    def add(self, guess):
        print guess
        self.db.add(guess)
    
    def create_menus(self):
        for cat in self.category_order:
            menu = Menu(cat)
            self.categories[cat] = menu
            self.add_item(menu)
        for cat, menu in self.categories.iteritems():
            for title in self.db.find(cat):
                print title
                detail = getDetail(title)
                menu.add_item_by_title_detail(detail, Menu)
        

class Config(object):
    global_config = None
    
    def __init__(self, args):
        self.layout = None
        self.root = None
        self.default_poster = None
        self.default_mplayer_opts = ["-novm", "-fs", "-utf8"]
        # Use SSA/ASS rendering to enable italics, bold, etc
        self.default_mplayer_opts.extend(["-ass", "-ass-color", "ffffff00", "-ass-font-scale", "1.4"])
    
    def parse_args(self, args):
        usage="usage: %prog file [file ...]"
        parser=OptionParser(usage=usage)
        parser.add_option("-v", action="store_true", dest="verbose", default=False)
        parser.add_option("-t", "--test", action="store_true", dest="test", default=False)
        (options, args) = parser.parse_args()
    
        self.root = RootMenu()
        if options.test:
            self.parse_dir(self.root, "test/movies1", "Movies")
            self.parse_dir(self.root, "test/movies2", "Movies")
            self.parse_dir(self.root, "test/series1", "TV")
            self.parse_dir(self.root, "test/series2", "TV")
        if args:
            for path in args:
                self.parse_dir(self.root, path)
        self.root.create_menus()
    
    def parse_dir(self, root, path, force_category=None):
        valid = self.get_video_extensions()
        for filename in iter_dir(path, valid):
            guess = guess_media_info(filename)
            root.add(guess)

    def get_video_extensions(self):
        return ['.vob', '.mp4', '.avi', '.wmv', '.mov', '.mpg', '.mpeg', '.mpeg4', '.mkv', '.flv', '.webm']
    
    def get_root(self, window):
        return self.root
    
    def get_layout(self, window):
        return MenuDetail2ColumnLayout(window, self)
    
    def get_font_name(self):
        return "Helvetica"
    
    def get_font_size(self):
        return 20
    
    def get_selected_font_size(self):
        return 26

    def get_title_renderer(self, window, box, fonts):
        return TitleRenderer(window, box, fonts, self)

    def get_menu_renderer(self, window, box, fonts):
        return VerticalMenuRenderer(window, box, fonts, self)

    def get_detail_renderer(self, window, box, fonts):
        return DetailRenderer(window, box, fonts, self)
    
    def get_default_poster(self):
        if self.default_poster is None:
            self.default_poster = pyglet.image.load("graphics/artwork-not-available.png")
        return self.default_poster
    
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
    Config.global_config = Config(args)
    conf = get_global_config()
    conf.parse_args(args)
    return conf

def get_global_config():
    return Config.global_config

def iter_dir(path, valid_extensions=None, exclude=None):
    if exclude is not None:
        try:
            exclude = re.compile(exclude)
        except:
            print("Invalid regular expression %s" % exclude)
            pass
    videos = glob.glob(os.path.join(path, "*"))
    for video in videos:
        valid = False
        if os.path.isdir(video):
            if not video.endswith(".old"):
                if exclude:
                    match = cls.exclude.search(video)
                    if match:
                        if cls.verbose: print("Skipping dir %s" % video)
                        continue
                print("Checking dir %s" % video)
                yield video
        elif os.path.isfile(video):
            print("Checking %s" % video)
            if valid_extensions:
                for ext in valid_extensions:
                    if video.endswith(ext):
                        valid = True
                        print ("Found valid media: %s" % video)
                        break
            else:
                valid = True
            if valid:
                yield video
