import os, logging, urllib

import imdb
import tmdb3
from ..third_party.tvdb_api import tvdb_api, tvdb_exceptions

from ..utils import FilePickleDict

log = logging.getLogger("dinoteeth.proxies")

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
    def __init__(self, base_dir, imdb_cache_dir="imdb-cache", tmdb_cache_dir="tmdb-cache", tvdb_cache_dir="tvdb-cache", language="en"):
        if base_dir:
            if imdb_cache_dir is not None:
                imdb_cache_dir = os.path.join(base_dir, imdb_cache_dir)
            if tmdb_cache_dir is not None:
                tmdb_cache_dir = os.path.join(base_dir, tmdb_cache_dir)
            if tvdb_cache_dir is not None:
                tvdb_cache_dir = os.path.join(base_dir, tvdb_cache_dir)
        self.imdb_api = IMDbFileProxy(imdb_cache_dir)
        self.tmdb_api = TMDbFileProxy(tmdb_cache_dir)
        self.tvdb_api = TVDbFileProxy(tvdb_cache_dir)
        self.language = language




from ..download import DownloadTask

import types
from imdb import Movie

def replaced_retrieve(self, url, size=-1, _noCookies=False):
    print url
    return url

def search_results_from_http_data(self, cont, results):
    print cont
    res = self.smProxy.search_movie_parser.parse(cont, results=results)['data']
    print res
    return [Movie.Movie(movieID=self._get_real_movieID(mi),
                        data=md, modFunct=self._defModFunct,
                        accessSystem=self.accessSystem) for mi, md in res][:results]
    

class IMDbProxy(object):
    def __init__(self, base_dir, imdb_cache_dir="imdb-cache", language="en"):
        if base_dir:
            if imdb_cache_dir is not None:
                imdb_cache_dir = os.path.join(base_dir, imdb_cache_dir)
        self.search_cache = FilePickleDict(imdb_cache_dir, "s")
        self.api = imdb.IMDb(accessSystem='http', adultSearch=1)
        self.api._retrieve = types.MethodType(replaced_retrieve, self.api)
        self.api.search_results_from_http_data = types.MethodType(search_results_from_http_data, self.api)
        self.language = language
    
    def search_url(self, title, num_results=20):
        return self.api._get_search_content('tt', title, num_results)
    
    def search_results_from_data(self, data, num_results=20):
        return self.api.search_results_from_http_data(data, num_results)

class IMDbSearchTask(DownloadTask):
    def __init__(self, api, title, num_results=20):
        self.api = api
        self.title = title
        self.num_results = num_results
        url = self.api.search_url(title, num_results)
        self.path = os.path.join("/tmp", urllib.quote_plus(url))
        DownloadTask.__init__(self, url, self.path, include_header=False)
    
    def _is_cached(self):
        return self.title in self.api.search_cache or os.path.exists(self.path)
        
    def success_callback(self):
        if self.title in self.api.search_cache:
            log.debug("*** FOUND %s in search cache: " % self.title)
            results = self.api.search_cache[self.title]
        else:
            log.debug("*** NOT FOUND in search cache: %s" % self.title)
            if os.path.exists(self.path):
                self.data = open(self.path).read()
            results = self.api.search_results_from_data(self.data, self.num_results)
            log.debug("*** STORING %s in search cache: " % self.title)
            self.api.search_cache[self.title] = results
        for result in results:
            result.imdb_id = "tt" + result.movieID
            print result.imdb_id, result
        self.results = results
