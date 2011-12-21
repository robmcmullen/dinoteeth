import os, sys, glob, re
import pyglet
from optparse import OptionParser

from view import *
from model import MenuItem
from database import DictDatabase
from media import guess_media_info, guess_custom, normalize_guess, MediaObject
from theme import MenuTheme
from mplayer import MPlayerClient, MPlayerInfo
from utils import decode_title_text, ArtworkLoader
from metadata import UnifiedMetadataDatabase, UnifiedMetadata

class RootMenu(MenuItem):
    def __init__(self, db, menu_theme):
        MenuItem.__init__(self, "Dinoteeth Media Launcher", theme=menu_theme)
        self.db = db
        self.metadata = {
            'special': 'root',
            'image': '../../graphics/background-merged.jpg',
            }
        
        self.category_order = [
#            ("Movies", self.get_movies_genres),
            ("TV", self.get_tv_root),
            ("Photos", self.get_empty_root),
            ("Games", self.get_empty_root),
            ("Paused...", self.get_empty_root),
            ]
        self.categories = {}
    
    def create_menus(self):
        self.create_movies_genres()
        for cat, populate in self.category_order:
            menu = MenuItem(cat, populate=populate)
            self.add(menu)
    
    def create_movies_genres(self, *args):
        menu = MenuItem("Movies")
        menu.metadata = {'special': 'movies'}
        self.add(menu)
        results = self.db.find("movie")
        entry = MenuItem("All", populate=self.get_movies_root)
        entry.metadata = menu.metadata
        menu.add(entry)
        genres = sorted(list(results.all_metadata('genres')))
        for genre in genres:
            subset = results.subset_by_metadata('genres', genre)
            entry = MenuItem(genre, populate=subset.hierarchy)
            menu.add(entry)
    
    def get_movies_root(self, *args):
        results = self.db.find("movie")
        h = results.hierarchy()
        print h
        return h
    
    def get_tv_root(self, *args):
        results = self.db.find("episode")
        h = results.hierarchy()
        return h
    
    def get_empty_root(self, *args):
        results = self.db.find("nothing")
        h = results.hierarchy()
        return h
    
    def save_state(self):
        self.db.saveStateToFile()


class Config(object):
    global_config = None
    
    def __init__(self, args, parser=None):
        self.layout = None
        self.root = None
        self.default_poster = None
        self.default_mplayer_opts = ["-novm", "-fs", "-utf8"]
        # Use SSA/ASS rendering to enable italics, bold, etc
        self.default_mplayer_opts.extend(["-ass", "-ass-color", "ffffff00", "-ass-font-scale", "1.4"])
        if parser is None:
            parser = self.get_arg_parser()
        self.parse_args(args, parser)
    
    @classmethod
    def get_arg_parser(self):
        usage="usage: %prog file [file ...]"
        parser=OptionParser(usage=usage)
        parser.add_option("-v", action="store_true", dest="verbose", default=False)
        parser.add_option("-t", "--test", action="store_true", dest="test", default=False)
        parser.add_option("-d", "--database", action="store", dest="database", default="dinoteeth.db")
        parser.add_option("-m", "--metadata-database", action="store", dest="umdb", default="dinoteeth.umdb")
        parser.add_option("-i", "--image-dir", action="store", dest="image_dir", default="test/graphics")
        return parser
    
    def parse_args(self, args, parser):
        self.parser = parser
        (self.options, self.args) = self.parser.parse_args()
    
        self.db = self.get_database()
        self.umdb = self.get_metadata_database()
        MediaObject.setMetadataDatabase(self.umdb)
        MediaObject.setIgnoreLeadingArticles(self.get_leading_articles())
        self.theme = self.get_menu_theme()
        if self.options.test:
            self.parse_dir(self.db, "test/movies1", "movie")
            self.parse_dir(self.db, "test/movies2", "movie")
            self.parse_dir(self.db, "test/series1", "episode")
            self.parse_dir(self.db, "test/series2", "episode")
            self.db.saveStateToFile()
        if self.args:
            for path in self.args:
                self.parse_dir(self.db, path)
            self.db.saveStateToFile()
    
    def create_root(self):
        self.root = RootMenu(self.db, self.theme)
        self.root.create_menus()
    
    def get_database(self):
        scanner = self.get_metadata_scanner()
        db = DictDatabase(media_scanner=scanner)
        db.loadStateFromFile(self.options.database)
        return db
    
    def get_metadata_scanner(self):
        return MPlayerInfo
    
    def get_metadata_database(self):
        umdb = UnifiedMetadataDatabase()
        umdb.loadStateFromFile(self.options.umdb)
        return umdb
    
    def parse_dir(self, db, path, force_category=None):
        valid = self.get_video_extensions()
        regexps = self.get_custom_video_regexps()
        for pathname in iter_dir(path, valid):
            if not db.is_current(pathname):
                filename = decode_title_text(pathname)
                guess = None
                if regexps:
                    guess = guess_custom(filename, regexps)
                if not guess:
                    guess = guess_media_info(filename)
                guess['pathname'] = pathname
                db.add(guess)
        self.db.saveStateToFile()

    def get_video_extensions(self):
        return ['.vob', '.mp4', '.avi', '.wmv', '.mov', '.mpg', '.mpeg', '.mpeg4', '.mkv', '.flv', '.webm']
    
    def get_custom_video_regexps(self):
        return [
            r"(.+/)*(?P<series>.+)-[Ss](?P<season>[0-9]{1,2})-?[Ee](?P<episodeNumber>[0-9]{1,2})-?(?P<title>.+)?",
            r"(.+/)*(?P<series>.+)-[Ss](?P<season>[0-9]{1,2})-?[Xx](?P<extraNumber>[0-9]{1,2})-?(?P<title>.+)?",
            r"(.+/)*(?P<franchise>.+)-[Ff](?P<episodeNumber>[0-9]{1,2})(-(?P<title>.+))(-[Xx](?P<extraNumber>[0-9]{1,2}))(-(?P<extraTitle>.+))?",
            r"(.+/)*(?P<franchise>.+)-[Ff](?P<episodeNumber>[0-9]{1,2})(-[Xx](?P<extraNumber>[0-9]{1,2}))(-(?P<extraTitle>.+))?",
            r"(.+/)*(?P<title>.+)-[Xx](?P<extraNumber>[0-9]{1,2})(-(?P<extraTitle>.+))?",
            r"(.+/)*(?P<franchise>.+)-[Ff](?P<episodeNumber>[0-9]{1,2})(-(?P<title>.+))?",
            ]
    
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
    
    def get_menu_theme(self):
        return MenuTheme()
    
    def get_artwork_loader(self):
        return ArtworkLoader(self.options.image_dir, "graphics/artwork-not-available.png")
    
    def get_media_client(self):
        return MPlayerClient(self)
    
    def get_mplayer_opts(self, path):
        opts = self.default_mplayer_opts[:]
        root, ext = os.path.splitext(path)
        # do something with path if desired
        return opts
    
    def get_leading_articles(self):
        return ["a", "an", "the"]
    
    def save_state(self):
        self.root.save_state()


def setup(args):
    Config.global_config = Config(args)
    conf = get_global_config()
    conf.create_root()
    return conf

def get_global_config():
    return Config.global_config

def iter_dir(path, valid_extensions=None, exclude=None, verbose=False):
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
                        if verbose: print("Skipping dir %s" % video)
                        continue
                if verbose: print("Checking dir %s" % video)
                yield video
        elif os.path.isfile(video):
            if verbose: print("Checking %s" % video)
            if valid_extensions:
                for ext in valid_extensions:
                    if video.endswith(ext):
                        valid = True
                        if verbose: print ("Found valid media: %s" % video)
                        break
            else:
                valid = True
            if valid:
                yield video
