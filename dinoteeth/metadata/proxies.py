import os, logging

import imdb
import tmdb3
from ..third_party.tvdb_api import tvdb_api, tvdb_exceptions

log = logging.getLogger("dinoteeth.proxies")


class FilePickleDict(object):
    """Emulated dictionary that stores items on the filesystem as pickles
    
    """
    def __init__(self, pathname, prefix="x", non_empty_to_save=True):
        self.root = pathname
        self.prefix = prefix
        self.non_empty_to_save = non_empty_to_save
        if not os.path.exists(self.root):
            os.mkdir(self.root)
        elif os.path.exists(self.root) and not os.path.isdir(self.root):
            raise RuntimeError("%s is not a directory" % self.root)

    def __getitem__(self, key):
        import cPickle as pickle

        filename = self.pathname_from_key(key)
        if os.path.exists(filename):
            with open(filename, "rb") as fh:
                bytes = fh.read()
                try:
                    data = pickle.loads(bytes)
                except ImportError:
                    data = pickle_loads_renamed(bytes)
            return data

    def __setitem__(self, key, value):
        import cPickle as pickle

        if self.non_empty_to_save and not bool(value):
            # Don't save empty values if requested not to
            return
        filename = self.pathname_from_key(key)
        bytes = pickle.dumps(value)
        with open(filename, "wb") as fh:
            fh.write(bytes)
    
    def __contains__(self, key):
        filename = self.pathname_from_key(key)
        return os.path.exists(filename)
    
    def filename_from_key(self, key):
        """Method to generate a filesystem-safe name representing the key
        
        Default mapping uses url encoding
        """
        import urllib
        return self.prefix + urllib.quote_plus(unicode(key).encode('utf8'))
    
    def pathname_from_key(self, key):
        return os.path.join(self.root, self.filename_from_key(key))

class FileProxy(object):
    def __init__(self, cache_dir=None):
        self.create_api_connection()
        if cache_dir:
            self.search_cache = FilePickleDict(cache_dir, "s")
            self.movie_obj_cache = FilePickleDict(cache_dir, "")
            self.use_cache = True
        else:
            self.search_cache = {}
            self.movie_obj_cache = {}
            self.use_cache = False
        
    def __str__(self):
        lines = []
        titles = sorted(self.search_cache.keys())
        for title in titles:
            lines.append("%s: %s" % (title, self.search_cache[title]))
        return "\n".join(lines)
    
    def create_api_connection(self):
        raise RuntimeError()
        
class IMDbFileProxy(FileProxy):
    def create_api_connection(self):
        self.imdb_api = imdb.IMDb(accessSystem='http', adultSearch=1)
        
    def search_movie(self, title):
        if title in self.search_cache:
            log.debug("*** FOUND %s in search cache: " % title)
            results = self.search_cache[title]
        else:
            log.debug("*** NOT FOUND in search cache: %s" % title )
            try:
                results = self.imdb_api.search_movie(title)
                if self.use_cache:
                    log.debug("*** STORING %s in search cache: " % title)
                    self.search_cache[title] = results
            except imdb.IMDbDataAccessError:
                results = []
        for result in results:
            result.imdb_id = "tt" + result.movieID
        return results
        
    def get_movie(self, imdb_id):
        if type(imdb_id) == int:
            imdb_id = "tt%07d" % imdb_id
        if imdb_id in self.movie_obj_cache:
            log.debug("*** FOUND %s in movie cache: " % imdb_id)
            movie_obj = self.movie_obj_cache[imdb_id]
        else:
            log.debug("*** NOT FOUND in movie cache: %s" % imdb_id)
            try:
                movie_obj = self.imdb_api.get_movie(imdb_id[2:])
                if self.use_cache and movie_obj:
                    log.debug("*** STORING %s in movie cache: " % imdb_id)
                    self.movie_obj_cache[imdb_id] = movie_obj
            except imdb.IMDbDataAccessError:
                movie_obj = None
        if movie_obj:
            movie_obj.imdb_id = "tt" + movie_obj.movieID
        return movie_obj

class TMDbFileProxy(FileProxy):
    def create_api_connection(self):
        self.tmdb_api = tmdb3.TMDb3_API()
    
    def get_imdb_id(self, imdb_id):
        if type(imdb_id) == int:
            imdb_id = "tt%07d" % imdb_id
        if not imdb_id.startswith("tt"):
            imdb_id = "tt" + imdb_id
        if imdb_id in self.movie_obj_cache:
            log.debug("*** FOUND %s in tmdb cache: " % imdb_id)
            return self.movie_obj_cache[imdb_id]
        log.debug("*** NOT FOUND in tmdb cache: %s" % imdb_id)
        movie_obj = self.tmdb_api.get_imdb_id(imdb_id)
        log.debug("*** STORING %s in tmdb cache: " % imdb_id)
        if self.use_cache:
            self.movie_obj_cache[imdb_id] = movie_obj
        return movie_obj

class TvdbSelectByIMDb:
    """Non-interactive UI for Tvdb_api which selects the result based on IMDb ID
    
    top_gear_australia_id = 1251819
    t = tvdb_api.Tvdb(custom_ui=TvdbSelectByIMDb(top_gear_australia_id))
    show = t['top gear']
    print show
    """
    def __init__(self, imdb_id):
        if type(imdb_id) == int:
            self.imdb_id = "tt%07d" % imdb_id
        elif not imdb_id.startswith("tt"):
            self.imdb_id = "tt%s" % imdb_id
        else:
            self.imdb_id = imdb_id

    def __call__(self, config):
        self.config = config
        return self

    def selectSeries(self, allSeries):
        for s in allSeries:
            id = s.get('imdb_id', 'no IMDb id')
            print "%s: %s %s" % (s['seriesname'], s.get('firstaired','unknown'), id)
            if id == self.imdb_id:
                return s
        return allSeries[0]

class TVDbFileProxy(object):
    def __init__(self, cache_dir=None):
        self.cache_dir = cache_dir
        if cache_dir:
            self.use_cache = True
        else:
            self.use_cache = False
        
    def search_movie(self, title):
        try:
            t = tvdb_api.Tvdb(custom_ui=TvdbSelectByIMDb(imdb_id), cache=self.cache_dir, banners=True)
            show = t[media.title]
        except tvdb_exceptions.tvdb_shownotfound:
            raise KeyError
        return results
        
    def get_imdb_id(self, imdb_id):
        try:
            t = tvdb_api.Tvdb(cache=self.cache_dir, banners=True)
            show = t[imdb_id]
        except tvdb_exceptions.tvdb_shownotfound:
            raise KeyError

        return show

class Proxies(object):
    def __init__(self, imdb_cache_dir=None, tmdb_cache_dir=None, tvdb_cache_dir=None, language="en"):
        self.imdb_api = IMDbFileProxy(imdb_cache_dir)
        self.tmdb_api = TMDbFileProxy(tmdb_cache_dir)
        self.tvdb_api = TVDbFileProxy(tvdb_cache_dir)
        self.language = language

