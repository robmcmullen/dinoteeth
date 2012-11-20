import os, logging, urllib

import imdb
import tmdb3
from ..third_party.tvdb_api import tvdb_api, tvdb_exceptions

from ..utils import FilePickleDict, HttpProxyBase

log = logging.getLogger("dinoteeth.proxies")


class TvdbPoster(object):
    def __init__(self, info):
        self.rating = float(info.get('rating','0'))
        self.num_votes = int(info.get('ratingcount','0'))
        self.url = info['_bannerpath']
        
    def __str__(self):
        return "rating=%s (%s votes): %s" % (self.rating, self.num_votes, self.url)

class TvdbPosterList(object):
    def __init__(self, season=-1):
        self.season = season
        self.posters = []
        self.num_with_votes = 0
        self.sum_rating = 0.0
        self.sum_votes = 0
        self.sorted = False
        
    def append(self, poster):
        self.posters.append(poster)
        if poster.num_votes > 0:
            self.num_with_votes += 1
            self.sum_rating += poster.rating
            self.sum_votes += poster.num_votes
        self.sorted = False
        
    def sort(self):
        """Sort using a bayesian average.
        
        Example from: http://www.thebroth.com/blog/118/bayesian-rating
        """
        if self.sorted:
            return True
        if self.num_with_votes == 0:
            return
        avg_num_votes = self.sum_votes / self.num_with_votes
        avg_rating = self.sum_rating / self.num_with_votes
        keylist = [(((avg_num_votes * avg_rating) + (p.num_votes * p.rating))/(avg_num_votes + p.num_votes), p) for p in self.posters]
        keylist.sort()
        keylist.reverse()
        posters = []
        for key, poster in keylist:
            print poster
            posters.append(poster)
        self.posters = posters
        self.sorted = True
        
    def best(self):
        if self.posters:
            self.sort()
            return self.posters[0]

class TvdbSeasonPosters(object):
    def __init__(self):
        self.seasons = {}
        
    def add(self, info):
        poster = TvdbPoster(info)
        s = int(info['season'])
        if s not in self.seasons:
            self.seasons[s] = TvdbPosterList(s)
        self.seasons[s].append(poster)
        
    def sort(self):
        seasons = self.seasons.keys()
        seasons.sort()
        for s in seasons:
            print "Season %d" % s
            self.seasons[s].sort()
            
    def best(self, season):
        if season in self.seasons:
            return self.seasons[season].best()
    
    def get_seasons(self):
        s = self.seasons.keys()
        s.sort()
        return s

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

class TVDbFileProxy(HttpProxyBase):
    def __init__(self, cache_dir=None, language="en"):
        HttpProxyBase.__init__(self, cache_dir)
        self.language = language
        
    def search_movie(self, title):
        try:
            t = tvdb_api.Tvdb(custom_ui=TvdbSelectByIMDb(imdb_id), cache=self.http_cache_dir, banners=True)
            show = t[media.title]
        except tvdb_exceptions.tvdb_shownotfound:
            raise KeyError
        return results
        
    def get_imdb_id(self, imdb_id):
        if imdb_id is None:
            raise KeyError
        try:
            t = tvdb_api.Tvdb(cache=self.http_cache_dir, banners=True)
            show = t[imdb_id]
        except tvdb_exceptions.tvdb_shownotfound:
            raise KeyError

        return show
        
    # Tvdb specific poster lookup
    # second level dictionary keys
    fanart_key='fanart'
    banner_key='series'
    poster_key='poster'
    season_key='season'
    # third level dictionay keys for select graphics URL(s)
    poster_series_key='680x1000'
    poster_season_key='season'
    fanart_hires_key='1920x1080'
    fanart_lowres_key='1280x720'
    banner_series_key='graphical'
    banner_season_key='seasonwide'

    def best_poster_url(self, show):
        posters = show.data['_banners'][self.poster_key][self.poster_series_key]
        series = TvdbPosterList()
        for k,info in posters.iteritems():
            if info['language'] != self.language:
                continue
            p = TvdbPoster(info)
            series.append(p)
        best = series.best()
        if best:
            return best.url
        return None
        
    def best_season_poster_urls(self, show):
        posters = show.data['_banners'][self.season_key][self.poster_season_key]
        seasons = TvdbSeasonPosters()
        for k,info in posters.iteritems():
            if info['language'] != self.language:
                continue
            seasons.add(info)
        seasons.sort()
        url_map = {}
        for i in seasons.get_seasons():
            best = seasons.best(i)
            log.debug("best poster for season #%d: %s" % (i, best))
            url_map[i] = best.url
        return url_map
    
    def fetch_poster_urls(self, show):
        main = self.best_poster_url(show)
        season_map = self.best_season_poster_urls(show)
        return main, season_map

class Proxies(object):
    def __init__(self, settings):
        base_dir = settings.metadata_root
        for subdir in ["imdb_cache_dir", "tmdb_cache_dir", "tvdb_cache_dir"]:
            path = getattr(settings, subdir)
            if not path:
                path = base_dir
            elif not os.path.isabs(path):
                path = os.path.join(base_dir, path)
            setattr(self, subdir, path)
        self.imdb_api = IMDbProxy(self.imdb_cache_dir, settings.imdb_language)
        self.tmdb_api = tmdb3.TMDb3_API(self.tmdb_cache_dir, settings.iso_639_1, settings.tmdb_poster_size)
        self.tvdb_api = TVDbFileProxy(self.tvdb_cache_dir, settings.iso_639_1)




from ..download import DownloadTask

import types
from imdb import Movie

def replaced_retrieve(self, url, size=-1, _noCookies=False):
    print url
    return url

class IMDbProxy(HttpProxyBase):
    def __init__(self, imdb_cache_dir, language="en"):
        HttpProxyBase.__init__(self, imdb_cache_dir)
        self.search_cache = FilePickleDict(imdb_cache_dir, "s")
        self.movie_obj_cache = FilePickleDict(imdb_cache_dir, "")
        self.api = imdb.IMDb(accessSystem='http', adultSearch=1)
        self.api._retrieve = types.MethodType(replaced_retrieve, self.api)
        self.http_api = imdb.IMDb(accessSystem='http', adultSearch=1)
        self.language = language
    
    def search_url(self, title, num_results=20):
        return self.api._get_search_content('tt', title, num_results)
    
    def search_results_from_data(self, data, num_results=20):
        res = self.api.smProxy.search_movie_parser.parse(data, results=num_results)['data']
        print res
        return [Movie.Movie(movieID=self.api._get_real_movieID(mi),
                            data=md, modFunct=self.api._defModFunct,
                            accessSystem=self.api.accessSystem) for mi, md in res][:num_results]
    
    def process_search(self, data, title, num_results):
        results = self.search_results_from_data(data, num_results)
        log.debug("*** STORING %s in search cache: " % title)
        for result in results:
            result.imdb_id = "tt" + result.movieID
            print result.imdb_id, result
        self.search_cache[title] = results
        return results
    
    def search_movie(self, title, num_results=20):
        if title in self.search_cache:
            log.debug("*** FOUND %s in search cache: " % title)
            results = self.search_cache[title]
        else:
            log.debug("*** NOT FOUND in search cache: %s" % title)
            url = self.search_url(title, num_results)
            data = self.load_url(url)
            results = self.process_search(data, title, num_results)
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
                movie_obj = self.http_api.get_movie(imdb_id[2:])
                log.debug("*** STORING %s in movie cache: " % imdb_id)
                if movie_obj:
                    movie_obj.imdb_id = "tt" + movie_obj.movieID
                self.movie_obj_cache[imdb_id] = movie_obj
            except imdb.IMDbDataAccessError:
                movie_obj = None
        return movie_obj

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
        self.path = os.path.join(api.http_cache, urllib.quote_plus(url))
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

class TMDbMovieBestPosterTask(DownloadTask):
    def __init__(self, api, movie):
        self.api = api
        self.movie = movie
        url = self.movie.get_best_poster_url()
        self.path = self.api.get_cache_path(url)
        DownloadTask.__init__(self, url, self.path, include_header=False)
    
    def _is_cached(self):
        return os.path.exists(self.path)
        
    def success_callback(self):
        print "downloaded poster %s: %s" % (self.movie.movie['title'], os.path.getsize(self.path))

