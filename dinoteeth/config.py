import os, sys, glob, re, logging
try:
    import argparse
except:
    import third_party.argparse as argparse
from third_party.configobj import ConfigObj

from view import *
from proxies import Proxies
from database import DBFacade, NewDatabase
from updates import UpdateManager, FileWatcher
from mplayer import MPlayerClient
from utils import decode_title_text
from image import ArtworkLoader, ScaledArtworkLoader
from posters import PosterFetcher
from thumbnail import ThumbnailFactory
from hierarchy import RootMenu
from photo import PhotoDB
from media import enzyme_extensions
from metadata import BaseMetadata
import i18n

logging.basicConfig(level=logging.WARNING)

log = logging.getLogger("dinoteeth")
#log.setLevel(logging.DEBUG)
otherlog = logging.getLogger("dinoteeth.metadata")
#otherlog.setLevel(logging.DEBUG)
otherlog = logging.getLogger("dinoteeth.utils")
#otherlog.setLevel(logging.DEBUG)


class Config(object):
    global_config = None
    
    def __init__(self, args, parser=None):
        self.layout = None
        self.main_window = None
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
        parser = argparse.ArgumentParser(description="Dinoteeth Media System", conflict_handler='resolve')
        parser.add_argument("-c", "--conf_file",
                    help="Specify config file", metavar="FILE")
        parser.add_argument("-v", "--verbose", action="count", default=0)
        parser.add_argument("--ui", action="store", default="sdl")
        parser.add_argument("--metadata-root", action="store", default="",
                          help="Default metadata/database root directory for those databases and the image directories that don't specify a full path")
        parser.add_argument("--db", action="store", dest="database", default="dinoteeth.zodb")
        parser.add_argument("--db-host", action="store", dest="db_host", default="")
        parser.add_argument("--imdb-cache-dir", action="store", default="imdb-cache")
        parser.add_argument("--tmdb-cache-dir", action="store", default="tmdb-cache")
        parser.add_argument("--tvdb-cache-dir", action="store", default="tvdb-cache")
        parser.add_argument("--thumbnail-dir", action="store", default="")
        parser.add_argument("-i", "--image-dir", action="store", dest="image_dir", default="graphics")
        parser.add_argument("--poster-width", action="store", type=int, default=-1, help="Maximum displayed poster width")
        parser.add_argument("--media-root", action="store", default="",
                          help="Media under this directory will be stored in the database as relative paths, permitting the structure to be moved to other machines without rebuilding the database")
        parser.add_argument("-l", "--language", action="store", default="en")
        parser.add_argument("-w", "--window", action="store_false", dest="fullscreen", default=True)
        parser.add_argument("--window-width", action="store", type=int, default=1280)
        parser.add_argument("--window-height", action="store", type=int, default=720)
        parser.add_argument("--top-margin", action="store", type=int, default=0)
        parser.add_argument("--right-margin", action="store", type=int, default=0)
        parser.add_argument("--bottom-margin", action="store", type=int, default=0)
        parser.add_argument("--left-margin", action="store", type=int, default=0)
        
        parser.add_argument("--font-name", action="store", default="Arial")
        parser.add_argument("--font-size-menu", action="store", type=int, default=16)
        parser.add_argument("--font-size-detail", action="store", type=int, default=12)
        parser.add_argument("--font-size-selected", action="store", type=int, default=24)
        
        parser.add_argument("--imdb-country-code", action="store", default="USA")
        parser.add_argument("--imdb-language", action="store", default="English")
        parser.add_argument("--country-code", action="store", default="US")
        parser.add_argument("--test-threads", action="store_true", default=False)
        return parser
    
    def parse_args(self, args, parser):
        default_parser = argparse.ArgumentParser(description="Default Parser")
        default_parser.add_argument("-c", "--conf_file", default="",
                    help="Specify config file to replace global config file loaded from user's home directory", metavar="FILE")
        options, extra_args = default_parser.parse_known_args()
        defaults = {}
        conf_file = os.path.expanduser("~/.dinoteeth/settings.ini")
        if options.conf_file:
            conf_file = options.conf_file
        self.ini = ConfigObj(conf_file)
        if "defaults" in self.ini:
            defaults = dict(self.ini["defaults"])
        
        if "media_paths" not in self.ini:
            self.ini["media_paths"] = {}
        
        parser.set_defaults(**defaults)
        self.parser = parser
        (self.options, self.args) = self.parser.parse_known_args(extra_args)
        
        debuglogs = ["dinoteeth.metadata", "dinoteeth.database"]
        if self.options.verbose == 1:
            level = logging.DEBUG
        elif self.options.verbose > 1:
            level = logging.INFO
        else:
            level = None
        if level:
            for name in debuglogs:
                log = logging.getLogger(name)
                log.setLevel(level)
        
        self.set_class_defaults()
        
        self.proxies = self.get_proxies()
        self.db = self.get_database()
        if self.args:
            for path in self.args:
                if path not in self.ini["media_paths"]:
                    self.ini["media_paths"][path] = "autodetect"
        
        if not options.conf_file:
            # Save the configuration in the global file as long as it's not
            # a user-specified config file.  User specified files aren't
            # overwritten, nor are user specified files saved in the global
            # file
            self.save_global_config_file()
        self.pdb = self.get_photo_database()
    
    def get_config_file_name(self):
        conf_file = os.path.expanduser("~/.dinoteeth/settings.ini")
        return conf_file
    
    def save_global_config_file(self):
        name = self.get_config_file_name()
        if not os.path.exists(name):
            confdir = os.path.dirname(name)
            if not os.path.exists(confdir):
                try:
                    os.mkdir(confdir)
                except:
                    log.error("Can't create configuration directory %s" % confdir)
                    return
        try:
            with open(name, "w") as fh:
                self.ini.write(fh)
        except Exception, e:
            log.error("Can't save configuration file %s: %s" % (name, e))
    
    def set_class_defaults(self):
        BaseMetadata.imdb_country = self.options.imdb_country_code
        BaseMetadata.imdb_language = self.options.imdb_language
        BaseMetadata.iso_3166_1 = self.options.country_code
    
    def get_main_window_class(self):
        if self.options.ui == "sdl":
            from ui.sdl_ui import SdlMainWindow
            return SdlMainWindow
        elif self.options.ui == "pyglet":
            from ui.pyglet_ui import PygletMainWindow
            return PygletMainWindow
        raise RuntimeError("Unknown user interface: %s" % self.options.ui)
    
    def get_main_window(self):
        if self.main_window is None:
            margins = (self.options.top_margin, self.options.right_margin,
                       self.options.bottom_margin, self.options.left_margin)
            wincls = self.get_main_window_class()
            self.main_window = wincls(self, fullscreen=self.options.fullscreen,
                                      width=self.options.window_width,
                                      height=self.options.window_height,
                                      margins=margins,
                                      thumbnails=self.get_thumbnail_loader())
            
            UpdateManager(self.main_window, 'on_status_update', self.db, self.get_thumbnail_loader())
            if self.options.test_threads:
                UpdateManager.test()
        return self.main_window
    
    def prepare_for_external_app(self):
        win = self.get_main_window()
        win.set_using_external_app(True, self.options.fullscreen)
    
    def restore_after_external_app(self):
        win = self.get_main_window()
        win.set_using_external_app(False, self.options.fullscreen)
    
    def create_root(self):
        self.root = RootMenu(self)
    
    def get_metadata_pathname(self, option):
        if not os.path.isabs(option) and self.options.metadata_root:
            if not os.path.exists(self.options.metadata_root):
                os.mkdir(self.options.metadata_root)
            option = os.path.join(self.options.metadata_root, option)
        log.debug("database: %s" % option)
        return option
    
    def get_object_database(self):
        if not hasattr(self, 'zodb'):
            self.zodb = DBFacade(self.get_metadata_pathname(self.options.database), self.options.db_host)
        return self.zodb
    
    def get_photo_database(self):
        db = PhotoDB()
        if 'photo_paths' in self.ini:
            for path, flags in self.ini["photo_paths"].iteritems():
                db.add_path(path)
        return db
    
    def get_proxies(self):
        proxies = Proxies(
            imdb_cache_dir=self.get_metadata_pathname(self.options.imdb_cache_dir),
            tmdb_cache_dir=self.get_metadata_pathname(self.options.tmdb_cache_dir),
            tvdb_cache_dir=self.get_metadata_pathname(self.options.tvdb_cache_dir),
            language=self.options.language)
        return proxies
    
    def get_poster_fetcher(self):
        return PosterFetcher(self.get_proxies(), self.get_artwork_loader().clone())
    
    def get_database(self):
        db = NewDatabase(self.get_object_database(), self.proxies)
        return db
    
    def start_update_monitor(self):
        valid = self.get_video_extensions()
        watcher = FileWatcher(self.db, self.get_video_extensions(), self.get_poster_fetcher())
        for path, flags in self.ini["media_paths"].iteritems():
            if self.options.media_root and not os.path.isabs(path):
                path = os.path.join(self.options.media_root, path)
            watcher.add_path(path, flags)
        watcher.watch()
    
    def get_video_extensions(self):
        """Get list of known video extensions from enzyme"""
        return enzyme_extensions()
    
    def get_root(self, window):
        return self.root
    
    def get_layout(self, window, margins):
        return MenuDetail2ColumnLayout(window, margins, self)
    
    def get_font_name(self):
        return self.options.font_name
    
    def get_font_size(self):
        return self.options.font_size_menu
    
    def get_detail_font_size(self):
        return self.options.font_size_detail
    
    def get_selected_font_size(self):
        return self.options.font_size_selected

    def get_title_renderer(self, window, box):
        return TitleRenderer(window, box, self)

    def get_menu_renderer(self, window, box):
        return VerticalMenuRenderer(window, box, self)

    def get_detail_renderer(self, window, box):
        return DetailRenderer(window, box, self)
    
    def get_artwork_loader(self):
        if not hasattr(self, "artwork_loader"):
            system_image_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../graphics"))
            na = os.path.join(system_image_dir, "artwork-not-available.png")
            full_size_loader = ArtworkLoader(self.get_metadata_pathname(self.options.image_dir), na)
            self.artwork_loader = ScaledArtworkLoader(full_size_loader, self.options.poster_width)
        return self.artwork_loader
    
    def get_thumbnail_loader(self):
        thumbnail_factory = ThumbnailFactory(self.options.thumbnail_dir)
        return thumbnail_factory
    
    def get_media_client(self):
        return MPlayerClient(self)
    
    def get_mplayer_opts(self, path):
        opts = self.default_mplayer_opts[:]
        root, ext = os.path.splitext(path)
        # do something with path if desired
        return opts
    
    def get_leading_articles(self):
        return ["a", "an", "the"]
    
    def show_status(self, text):
        win = self.get_main_window()
        win.on_status_update(text)
    
    def do_shutdown_tasks(self):
        self.db.pack()
        UpdateManager.stop_all()


def setup(args):
    Config.global_config = Config(args)
    conf = get_global_config()
    conf.create_root()
    return conf

def get_global_config():
    return Config.global_config
