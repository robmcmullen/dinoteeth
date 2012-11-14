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

class IMDbProxy(object):
    def __init__(self, base_dir, imdb_cache_dir="imdb-cache", language="en"):
        if base_dir:
            if imdb_cache_dir is not None:
                imdb_cache_dir = os.path.join(base_dir, imdb_cache_dir)
        self.search_cache = FilePickleDict(imdb_cache_dir, "s")
        self.movie_obj_cache = FilePickleDict(imdb_cache_dir, "")
        self.api = imdb.IMDb(accessSystem='http', adultSearch=1)
        self.api._retrieve = types.MethodType(replaced_retrieve, self.api)
        self.language = language
    
    def search_url(self, title, num_results=20):
        return self.api._get_search_content('tt', title, num_results)
    
    def search_results_from_data(self, data, num_results=20):
        res = self.api.smProxy.search_movie_parser.parse(data, results=num_results)['data']
        print res
        return [Movie.Movie(movieID=self.api._get_real_movieID(mi),
                            data=md, modFunct=self.api._defModFunct,
                            accessSystem=self.api.accessSystem) for mi, md in res][:num_results]

    def get_movie_main_url(self, movie_id):
        return self.api.urls['movie_main'] % movie_id + 'combined'
        
    def get_movie_plot_url(self, movie_id):
        return self.api.urls['movie_main'] % movie_id + 'plotsummary'
        
    def get_url_from_task(self, task):
        method = getattr(self, "get_movie_%s_url" % task.info_name)
        return method(task.movie_id)
    
    def get_blank_movie(self, movie_id):
        return Movie.Movie(movieID=movie_id, accessSystem=self.api.accessSystem)
        
    def get_movie_main_from_data(self, data):
        return self.api.mProxy.movie_parser.parse(data, mdparse=self.api._mdparse)
    
    def get_movie_plot_from_data(self, data):
        return self.api.mProxy.plot_parser.parse(data, getRefs=self.api._getRefs)
    
    def merge_movie_tasks(self, mop, tasks, override=0):
        res = {}
        for task in tasks:
            i = task.info_name
            if i in mop.current_info and not override:
                continue
            if not i:
                continue
            ret_method = getattr(self, "get_movie_%s_from_data" % i)
            ret = ret_method(task.data)
            keys = None
            if 'data' in ret:
                res.update(ret['data'])
                if isinstance(ret['data'], dict):
                    keys = ret['data'].keys()
            if 'info sets' in ret:
                for ri in ret['info sets']:
                    mop.add_to_current_info(ri, keys, mainInfoset=i)
            else:
                mop.add_to_current_info(i, keys)
            if 'titlesRefs' in ret:
                mop.update_titlesRefs(ret['titlesRefs'])
            if 'namesRefs' in ret:
                mop.update_namesRefs(ret['namesRefs'])
            if 'charactersRefs' in ret:
                mop.update_charactersRefs(ret['charactersRefs'])
        mop.set_data(res, override=0)


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

def safeprint(s):
    if isinstance(s, basestring):
        return unicode(s).encode('utf8')
    return s

def print_info(movie):
    keys = ['kind', 'title', 'canonical title', 'long imdb title', 'long imdb canonical title', 'smart canonical title', 'smart long imdb canonical title','akas', 'year', 'imdbIndex', 'certificates', 'mpaa', 'runtimes', 'rating', 'votes', 'genres', 'director', 'writer', 'producer', 'cast', 'writer', 'creator', 'original music', 'plot outline', 'number of seasons', 'number of episodes', 'series years', 'production companies' ]
    print sorted(movie.keys())
    print sorted(dir(movie))
    #for k,v in movie.iteritems():
    #    print "**%s**:   %s" % (safeprint(k), safeprint(v))
    for k in keys:
        if movie.has_key(k):
            print "%s: %s" % (k, safeprint(movie[k]))

class IMDbMovieDetailDownloadTask(DownloadTask):
    def __init__(self, api, imdb_id, info_name):
        self.api = api
        if imdb_id.startswith('tt'):
            movie_id = imdb_id[2:]
        else:
            movie_id = '%07d' % int(imdb_id)
            imdb_id = "tt" + movie_id
        self.imdb_id = imdb_id
        self.movie_id = movie_id
        self.info_name = info_name
        url = self.api.get_url_from_task(self)
        self.path = os.path.join("/tmp", urllib.quote_plus(url))
        DownloadTask.__init__(self, url, self.path, include_header=False)

class IMDbMovieDetailTask(IMDbMovieDetailDownloadTask):
    """
    imdb.get_movie(movie_id):
        movieID = imdb._normalize_movieID(movieID)
        movieID = imdb._get_real_movieID(movieID)
        movie = Movie.Movie(movieID=movieID)
        info = ('main', 'plot')
        imdb.update(movie, info)
            method = getattr(aSystem, 'get_%s_%s' %
                                    (prefix, i.replace(' ', '_')))
            # e.g.: get_movie_main, get_movie_plot
            ret = method(movieID)
    
    imdb.get_movie_main(movie_id):
        cont = self._retrieve(self.urls['movie_main'] % movieID + 'combined')
        return self.mProxy.movie_parser.parse(cont, mdparse=self._mdparse)

    """
    def __init__(self, api, imdb_id):
        IMDbMovieDetailDownloadTask.__init__(self, api, imdb_id, "main")
    
    def _is_cached(self):
        return self.imdb_id in self.api.movie_obj_cache or os.path.exists(self.path)
        
    def success_callback(self):
        if self.imdb_id not in self.api.movie_obj_cache:
            log.debug("*** NOT FOUND in movie cache: %s" % self.imdb_id)
            if os.path.exists(self.path):
                self.data = open(self.path).read()
            tasks = [IMDbMovieDetailDownloadTask(self.api, self.imdb_id, "plot")]
            return tasks
    
    def root_task_complete_callback(self):
        if self.imdb_id in self.api.movie_obj_cache:
            log.debug("*** FOUND %s in movie cache: " % self.imdb_id)
            self.movie_obj = self.api.movie_obj_cache[self.imdb_id]
        else:
            self.movie_obj = self.api.get_blank_movie(self.movie_id)
            tasks = [self]
            tasks.extend(self.children_scheduled)
            self.api.merge_movie_tasks(self.movie_obj, tasks)
            self.api.movie_obj_cache[self.imdb_id] = self.movie_obj
        print_info(self.movie_obj)
        log.debug("*** STORING %s in movie cache: " % self.imdb_id)



class TMDbAPITask(DownloadTask):
    def __init__(self, api):
        self.api = api
        url = self.api.get_conf_url()
        self.path = self.api.get_cache_path(url)
        DownloadTask.__init__(self, url, self.path, include_header=False)
    
    def _is_cached(self):
        return os.path.exists(self.path)
        
    def success_callback(self):
        if hasattr(self, 'data'):
            data = self.data
        elif os.path.exists(self.path):
            data = open(self.path).read()
        self.api.process_conf(data)
        print self.api.base_url
        print self.api.image_sizes

class TMDbMovieDetailDownloadTask(DownloadTask):
    def __init__(self, api, imdb_id, info_name):
        self.api = api
        if not imdb_id.startswith('tt'):
            movie_id = '%07d' % int(imdb_id)
            imdb_id = "tt" + movie_id
        self.imdb_id = imdb_id
        self.info_name = info_name
        url = self.api.get_url_from_task(self)
        print url
        self.path = self.api.get_cache_path(url)
        DownloadTask.__init__(self, url, self.path, include_header=False)

class TMDbMovieDetailSubTask(DownloadTask):
    def __init__(self, api, movie, info_name):
        self.api = api
        self.movie = movie
        self.info_name = info_name
        url = self.api.get_url_from_task(self, self.movie)
        self.path = self.api.get_cache_path(url)
        DownloadTask.__init__(self, url, self.path, include_header=False)
        
    def success_callback(self):
        if os.path.exists(self.path):
            self.data = open(self.path).read()
            self.movie.process_from_task(self)

class TMDbMovieDetailTask(TMDbMovieDetailDownloadTask):
    def __init__(self, api, imdb_id):
        TMDbMovieDetailDownloadTask.__init__(self, api, imdb_id, "main")
    
    def _is_cached(self):
        return self.imdb_id in self.api.movie_obj_cache or os.path.exists(self.path)
        
    def success_callback(self):
        if self.imdb_id not in self.api.movie_obj_cache:
            log.debug("*** NOT FOUND in movie cache: %s" % self.imdb_id)
            if os.path.exists(self.path):
                self.data = open(self.path).read()
                self.movie = self.api.get_movie(self.data)
                tasks = [TMDbMovieDetailSubTask(self.api, self.movie, "release_info"), TMDbMovieDetailSubTask(self.api, self.movie, "images")]
                return tasks
        else:
            self.movie = self.api.movie_obj_cache[self.imdb_id]
    
    def root_task_complete_callback(self):
        print self.movie
