import os, sys, glob, re, logging
try:
    import argparse
except:
    import dinoteeth.third_party.argparse as argparse
from dinoteeth.third_party.configobj import ConfigObj

from view import *
from database import MovieMetadataDatabase, MediaScanDatabase
from theme import MenuTheme
from mplayer import MPlayerClient
from utils import decode_title_text, ArtworkLoader
from hierarchy import RootMenu
from photo import PhotoDB
from media import enzyme_extensions
from metadata import BaseMetadata

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
        parser.add_argument("--metadata-root", action="store", default="",
                          help="Default metadata/database root directory for those databases and the image directories that don't specify a full path")
        parser.add_argument("--db", action="store", dest="database", default="dinoteeth.db")
        parser.add_argument("--mmdb", action="store", dest="mmdb", default="dinoteeth.mmdb")
        parser.add_argument("--imdb-cache-dir", action="store", default="imdb-cache")
        parser.add_argument("--tmdb-cache-dir", action="store", default="tmdb-cache")
        parser.add_argument("--tvdb-cache-dir", action="store", default="tvdb-cache")
        parser.add_argument("-i", "--image-dir", action="store", dest="image_dir", default="graphics")
        parser.add_argument("--poster-width", action="store", type=int, default=-1, help="Maximum displayed poster width")
        parser.add_argument("--media-root", action="store", default="",
                          help="Media under this directory will be stored in the database as relative paths, permitting the structure to be moved to other machines without rebuilding the database")
        parser.add_argument("-l", "--language", action="store", default="en")
        parser.add_argument("-w", "--window", action="store_false", dest="fullscreen", default=True)
        parser.add_argument("-p", "--photo-dir", action="append", dest="photo_dirs", default=None)
        parser.add_argument("--window-width", action="store", type=int, default=1280)
        parser.add_argument("--window-height", action="store", type=int, default=720)
        parser.add_argument("--top-margin", action="store", type=int, default=0)
        parser.add_argument("--right-margin", action="store", type=int, default=0)
        parser.add_argument("--bottom-margin", action="store", type=int, default=0)
        parser.add_argument("--left-margin", action="store", type=int, default=0)
        
        parser.add_argument("--imdb-country-code", action="store", default="USA")
        parser.add_argument("--country-code", action="store", default="US")
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
        
        debuglogs = ["dinoteeth.metadata", "dinoteeth.database", "dinoteeth.utils"]
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
        
        self.db = self.get_media_database()
        self.mmdb = self.get_metadata_database()
        self.theme = self.get_menu_theme()
        if self.args:
            for path in self.args:
                if path not in self.ini["media_paths"]:
                    self.ini["media_paths"][path] = "autodetect"
        self.update_metadata()
        
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
        BaseMetadata.iso_3166_1 = self.options.country_code
    
    def get_main_window(self):
        if self.main_window is None:
            margins = (self.options.top_margin, self.options.right_margin,
                       self.options.bottom_margin, self.options.left_margin)
            self.main_window = MainWindow(self, fullscreen=self.options.fullscreen,
                                          width=self.options.window_width,
                                          height=self.options.window_height,
                                          margins=margins)
        return self.main_window
    
    def prepare_for_external_app(self):
        win = self.get_main_window()
        if self.options.fullscreen:
            win.set_fullscreen(False)
    
    def restore_after_external_app(self):
        win = self.get_main_window()
        win.set_fullscreen(not self.options.fullscreen)
        win.set_fullscreen(self.options.fullscreen)
        win.activate()
    
    def create_root(self):
        self.root = RootMenu(self)
        self.root.create_menus()
    
    def get_metadata_pathname(self, option):
        if not os.path.isabs(option) and self.options.metadata_root:
            if not os.path.exists(self.options.metadata_root):
                os.mkdir(self.options.metadata_root)
            option = os.path.join(self.options.metadata_root, option)
        log.debug("database: %s" % option)
        return option
    
    def get_media_database(self):
        db = MediaScanDatabase()
        db.loadStateFromFile(self.get_metadata_pathname(self.options.database))
        return db
    
    def get_photo_database(self):
        db = PhotoDB()
        if self.options.photo_dirs:
            for path in self.options.photo_dirs:
                db.add_path(path)
        return db
    
    def get_metadata_database(self):
        mmdb = MovieMetadataDatabase(
            imdb_cache_dir=self.get_metadata_pathname(self.options.imdb_cache_dir),
            tmdb_cache_dir=self.get_metadata_pathname(self.options.tmdb_cache_dir),
            tvdb_cache_dir=self.get_metadata_pathname(self.options.tvdb_cache_dir),
            language=self.options.language)
        statefile = self.get_metadata_pathname(self.options.mmdb)
        print "Loading from %s" % statefile
        mmdb.loadStateFromFile(statefile)
        return mmdb
    
    def update_metadata(self):
        removed_keys, new_keys = self.parse_dirs(self.ini["media_paths"])
        if removed_keys:
            print "Found files that have been removed! %s" % str(removed_keys)
            self.remove_metadata(removed_keys)
        if new_keys:
            print "Found files that have been added! %s" % str(new_keys)
            self.add_metadata(new_keys)
        self.db.fix_missing_metadata(self.mmdb)
        self.db.saveStateToFile()
        self.mmdb.saveStateToFile()
    
    def remove_metadata(self, removed_keys):
        for i, key in enumerate(removed_keys):
            title_key = self.db.get_title_key(key)
            try:
                imdb_id = self.db.get_imdb_id(title_key)
            except KeyError:
                log.info("%d: orphaned title key %s has no imdb_id" % (i, str(title_key)))
                continue
            print "%d: removing imdb=%s %s" % (i, imdb_id, str(title_key))
            self.mmdb.remove(imdb_id)
            self.db.remove(key)
    
    def add_metadata(self, new_keys):
        artwork_loader = self.get_artwork_loader()
        count = len(new_keys)
        for i, key in enumerate(new_keys):
            title_key = self.db.get_title_key(key)
            try:
                imdb_id = self.db.get_imdb_id(title_key)
                print "%d/%d: imdb=%s %s" % (i, count, imdb_id, str(title_key))
            except KeyError:
                print "%d/%d: imdb=NOT FOUND %s" % (i, count, str(title_key))
                imdb_id = self.db.add_metadata_from_mmdb(title_key, self.mmdb)
                for j, media in enumerate(self.db.get_all_with_title_key(title_key)):
                    log.info("  media #%d: %s" % (j, str(media)))
            if imdb_id:
                if not self.mmdb.contains_imdb_id(imdb_id):
                    log.debug("Loading imdb_id %s" % imdb_id)
                    self.mmdb.fetch_imdb_id(imdb_id)
                if not artwork_loader.has_poster(imdb_id):
                    log.debug("Loading posters for imdb_id %s" % imdb_id)
                    self.mmdb.fetch_poster(imdb_id, artwork_loader)
    
    def parse_dirs(self, media_path_dict):
        stored_keys = self.db.known_keys()
        current_keys = set()
        for path, flags in media_path_dict.iteritems():
            print "Parsing path %s" % path
            self.parse_dir(self.db, path, flags, current_keys)
        self.db.saveStateToFile()
        removed_keys = stored_keys - current_keys
        new_keys = current_keys - stored_keys
        return removed_keys, new_keys
            
    def parse_dir(self, db, path, flags="", current_keys=None):
        valid = self.get_video_extensions()
        if self.options.media_root and not os.path.isabs(path):
            path = os.path.join(self.options.media_root, path)
        for pathname in iter_dir(path, valid):
            if not db.is_current(pathname, known_keys=current_keys):
                media_scan = db.add(pathname, flags, known_keys=current_keys)
                log.debug("added: %s" % db.get(media_scan.pathname))
#            entry = db.get(pathname)
#            log.debug("guess %s: %s" % (pathname, entry.guess))
#            log.debug("scan %s: %s" % (pathname, entry))

    def get_video_extensions(self):
        """Get list of known video extensions from enzyme"""
        return enzyme_extensions()
    
    def get_root(self, window):
        return self.root
    
    def get_layout(self, window, margins):
        return MenuDetail2ColumnLayout(window, margins, self)
    
    def get_font_name(self):
        return "Arial"
    
    def get_font_size(self):
        return 16
    
    def get_detail_font_size(self):
        return 12
    
    def get_selected_font_size(self):
        return 22

    def get_title_renderer(self, window, box, fonts):
        return TitleRenderer(window, box, fonts, self)

    def get_menu_renderer(self, window, box, fonts):
        return VerticalMenuRenderer(window, box, fonts, self)

    def get_detail_renderer(self, window, box, fonts):
        return DetailRenderer(window, box, fonts, self)
    
    def get_menu_theme(self):
        return MenuTheme()
    
    def get_artwork_loader(self):
        if not hasattr(self, "artwork_loader"):
            system_image_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../graphics"))
            na = os.path.join(system_image_dir, "artwork-not-available.png")
            print na
            self.artwork_loader = ArtworkLoader(self.get_metadata_pathname(self.options.image_dir), na, poster_width=self.options.poster_width)
        return self.artwork_loader
    
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

def iter_dir(path, valid_extensions=None, exclude=None, verbose=False, recurse=False):
    if exclude is not None:
        try:
            exclude = re.compile(exclude)
        except:
            log.warning("Invalid regular expression %s" % exclude)
            pass
    videos = glob.glob(os.path.join(path, "*"))
    for video in videos:
        valid = False
        if os.path.isdir(video):
            if not video.endswith(".old"):
                if exclude:
                    match = cls.exclude.search(video)
                    if match:
                        log.debug("Skipping dir %s" % video)
                        continue
                log.debug("Checking dir %s" % video)
                if recurse:
                    iter_dir(video, valid_extensions, exclude, verbose, True)
        elif os.path.isfile(video):
            log.debug("Checking %s" % video)
            if valid_extensions:
                for ext in valid_extensions:
                    if video.endswith(ext):
                        valid = True
                        log.debug("Found valid media: %s" % video)
                        break
            else:
                valid = True
            if valid:
                yield video
