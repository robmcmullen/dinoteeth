import os, sys, glob, re, logging
try:
    import argparse
except:
    import third_party.argparse as argparse
from third_party.configobj import ConfigObj
from third_party.validate import Validator

from view import *
from database import HomeTheaterDatabase
from model import MenuItem
from updates import UpdateManager, FileWatcher
from utils import DBFacade, decode_title_text, TitleKey
from thumbnail import ThumbnailFactory
from hierarchy import RootMenu
from photo import PhotoDB
import settings
import games
import home_theater
from clients import Client
import i18n

logging.basicConfig(level=logging.WARNING)

log = logging.getLogger("dinoteeth.config")

default_log_levels = {
    0: ["dinoteeth.config"],
    1: ["dinoteeth.database", "dinoteeth.hierarchy"],
    2: ["dinoteeth.metadata", "dinoteeth.model"],
    3: ["dinoteeth.home_theater", "dinoteeth.games"],
    }


class Config(object):
    global_config = None
    
    def __init__(self, args, parser=None):
        self.layout = None
        self.main_window = None
        self.root = None
        self.default_poster = None
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
        parser.add_argument("--test-threads", action="store_true", default=False)
        parser.add_argument("--test-menu", action="store_true", default=False)
        parser.add_argument("--test-menu-search", action="store", default="")
        
        # commands that can override settings in the [default] section; defaults
        # are provided by the configspec set in settings.default_conf
        parser.add_argument("--ui", action="store")
        parser.add_argument("-w", "--window", dest='fullscreen', action="store_false")
        parser.add_argument("--guest-mode", action="store_true")
        parser.add_argument("--default-subtitles", action="store_true")
        parser.add_argument("--immediate-rendering", dest='delayed_rendering', action="store_false")
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
        configspec = ConfigObj(settings.default_conf.splitlines(), list_values=False)
        self.ini = ConfigObj(conf_file, configspec=configspec)
        self.ini.validate(Validator())
        if "defaults" in self.ini:
            defaults = dict(self.ini["defaults"])
        
        if "media_paths" not in self.ini:
            self.ini["media_paths"] = {}
        
        parser.set_defaults(**defaults)
        self.parser = parser
        (self.options, self.args) = self.parser.parse_known_args(extra_args)
        
        verbosity = max(default_log_levels.keys())
        for v in range(verbosity + 1):
            if self.options.verbose >= v:
                level = logging.DEBUG
            else:
                level = logging.INFO
            for name in default_log_levels[v]:
                log = logging.getLogger(name)
                log.setLevel(level)
        
        self.set_class_defaults(self.ini, configspec)
        if self.options.verbose > 0:
            for k in dir(settings):
                if not k.startswith("_") and k != "default_conf":
                    print "%s: %s" % (k, getattr(settings, k))
        
        self.db = self.get_home_theater_database()
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
    
    def set_class_defaults(self, ini, configspec):
        # default section is overridden by command line arguments if specified
        section = "defaults"
        known = dict(configspec[section])
#        print "known [%s]: %s" % (section, known)
        for k in known.keys():
            setattr(settings, k, getattr(self.options, k))
        
        # parameters in other sections are only specified through config file
        for section in ["window", "fonts", "metadata", "metadata providers", "posters"]:
            user = dict(ini[section])
#            print "user [%s]: %s" % (section, user)
            known = dict(configspec[section])
#            print "known [%s]: %s" % (section, known)
            for k in known.keys():
                setattr(settings, k, user[k])
        
        user_title_key_map = {}
        if "title_key" in self.ini:
            items = self.ini['title_key']
            for encoded_title_key in items:
                imdb_id = items[encoded_title_key]
                title_key = TitleKey.get_from_encoded(encoded_title_key)
                user_title_key_map[title_key] = imdb_id
        settings.user_title_key_map = user_title_key_map
    
    def get_main_window_class(self):
        if settings.ui == "sdl":
            from ui.sdl_ui import SdlMainWindow
            return SdlMainWindow
        elif settings.ui == "pyglet":
            from ui.pyglet_ui import PygletMainWindow
            return PygletMainWindow
        raise RuntimeError("Unknown user interface: %s" % settings.ui)
    
    def get_main_window(self, factory):
        if self.main_window is None:
            margins = (settings.top_margin, settings.right_margin,
                       settings.bottom_margin, settings.left_margin)
            wincls = self.get_main_window_class()
            self.main_window = wincls(self, factory,
                                      fullscreen=settings.fullscreen,
                                      width=settings.window_width,
                                      height=settings.window_height,
                                      margins=margins,
                                      thumbnails=self.get_thumbnail_loader())
            
#            event_callback = self.main_window.get_event_callback('on_status_update')
            event_callback = self.main_window.get_event_callback('on_timer_tick')
            UpdateManager(event_callback, self.db, self.get_thumbnail_loader())
            if self.options.test_threads:
                UpdateManager.test()
        return self.main_window
    
    def prepare_for_external_app(self):
        win = self.main_window
        win.set_using_external_app(True, settings.fullscreen)
    
    def restore_after_external_app(self):
        win = self.main_window
        win.set_using_external_app(False, settings.fullscreen)
        self.refresh_database()
    
    def create_root(self):
        self.root = RootMenu(self)
    
    def get_metadata_pathname(self, option):
        if option is not None and not os.path.isabs(option) and settings.metadata_root:
            if not os.path.exists(settings.metadata_root):
                os.mkdir(settings.metadata_root)
            option = os.path.join(settings.metadata_root, option)
        log.debug("database: %s" % option)
        return option
    
    def get_object_database(self):
        if not hasattr(self, 'zodb'):
            self.zodb = DBFacade(self.get_metadata_pathname(settings.db_file), settings.db_host)
            self.zodb.add_commit_callback(MenuItem.needs_refresh)
        return self.zodb
    
    def get_photo_database(self):
        db = PhotoDB()
        if 'photo_paths' in self.ini:
            for path, flags in self.ini["photo_paths"].iteritems():
                db.add_path(path)
        return db
    
    def get_home_theater_database(self):
        db = HomeTheaterDatabase(self.get_object_database())
        return db
    
    def refresh_database(self):
        zodb = self.get_object_database()
        zodb.sync()
    
    def start_update_monitor(self):
        watcher = FileWatcher(self.db)
        for path, flags in self.ini["media_paths"].iteritems():
            if settings.media_root and not os.path.isabs(path):
                path = os.path.join(settings.media_root, path)
            watcher.add_path(path, flags)
        watcher.watch()
    
    def get_subtitle_extensions(self):
        return [".srt", ".ssa", ".ass"]
    
    def get_root(self, window):
        return self.root
    
    def get_font_name(self):
        return settings.font_name
    
    def get_font_size(self):
        return settings.font_size_menu
    
    def get_detail_font_size(self):
        return settings.font_size_detail
    
    def get_selected_font_size(self):
        return settings.font_size_selected
    
    def get_thumbnail_loader(self):
        thumbnail_factory = ThumbnailFactory(settings.thumbnail_dir, self.get_metadata_pathname(settings.image_dir))
        return thumbnail_factory
    
    def get_media_client(self, media_file):
        client = Client.get_loader(media_file)
        return client
    
    def get_leading_articles(self):
        return ["a", "an", "the"]
    
    def show_status(self, text):
        win = self.main_window
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
