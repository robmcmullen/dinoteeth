import os, logging

log = logging.getLogger("dinoteeth.posters")


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

class PosterFetcher(object):
    imdb_allowed_kinds = ['movie', 'video movie', 'tv movie', 'series', 'tv series', 'tv mini series']
    
    def __init__(self, proxies, artwork_loader):
        self.imdb_api = proxies.imdb_api
        self.tmdb_api = proxies.tmdb_api
        self.tvdb_api = proxies.tvdb_api
        self.artwork_loader = artwork_loader
        self.language = proxies.language
    
    def __str__(self):
        lines = []
        lines.append(u"Media:")
        for m in sorted(self.media.values()):
            lines.append(unicode(m))
        lines.append(u"People:")
        for p in sorted(self.people.values()):
            lines.append(u"  %s" % unicode(p))
        lines.append(u"Companies:")
        for c in sorted(self.companies.values()):
            lines.append(u"  %s" % unicode(c))
        return u"\n".join(lines)
    
    def has_poster(self, imdb_id):
        return self.artwork_loader.has_poster(imdb_id)
    
    def fetch_poster(self, imdb_id, media_category='movies'):
        if media_category == 'series':
            loaders = ['tvdb', 'tmdb']
        else:
            loaders = ['tmdb', 'tvdb']
        
        for loader in loaders:
            try:
                if loader == 'tvdb':
                    return self.fetch_poster_tvdb(imdb_id)
                elif loader == 'tmdb':
                    return self.fetch_poster_tmdb(imdb_id)
            except Exception, e:
                log.error("Error loading poster for %s: %s" % (imdb_id, e))
                pass
        return None
    
    # TMDb specific poster lookup
    def tmdb_poster_info(self, poster):
        urls = {}
        for key, url in poster.items():
            if url.startswith("http") and "/t/p/" in url:
                _, imginfo = url.split("/t/p/")
                size, filename = imginfo.split("/")
                if size.startswith("w") or size == "original":
                    urls[size] = url
                log.debug("%s: %s" % (size, url))
        return urls
    
    def fetch_poster_tmdb(self, imdb_id):
        tfilm = self.tmdb_api.get_imdb_id(imdb_id)
        if tfilm is None:
            raise KeyError
        found = tfilm.get_best_poster('w342', language=self.language)
        if found:
            log.debug("best poster: %s" % found)
            self.artwork_loader.save_poster_from_url(imdb_id, found)
        else:
            log.debug("No poster for %s" % unicode(tfilm).encode('utf8'))

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

    def fetch_poster_tvdb(self, imdb_id):
        show = self.tvdb_api.get_imdb_id(imdb_id)
        if not show:
            log.debug("No tvdb entry for %s" % imdb_id)
            return
        self.fetch_poster_tvdb_series(show, imdb_id)
        self.fetch_poster_tvdb_seasons(show, imdb_id)
        
    def fetch_poster_tvdb_series(self, show, imdb_id):
        posters = show.data['_banners'][self.poster_key][self.poster_series_key]
        series = TvdbPosterList()
        for k,info in posters.iteritems():
            if info['language'] != self.language:
                continue
            p = TvdbPoster(info)
            series.append(p)
        best = series.best()
        if best:
            log.debug("best poster: %s" % best)
            self.artwork_loader.save_poster_from_url(imdb_id, best.url)
        else:
            log.debug("No poster for %s" % imdb_id)
        
    def fetch_poster_tvdb_seasons(self, show, imdb_id):
        posters = show.data['_banners'][self.season_key][self.poster_season_key]
        seasons = TvdbSeasonPosters()
        for k,info in posters.iteritems():
            if info['language'] != self.language:
                continue
            seasons.add(info)
        seasons.sort()
        for i in seasons.get_seasons():
            best = seasons.best(i)
            log.debug("best poster for season #%d: %s" % (i, best))
            self.artwork_loader.save_poster_from_url(imdb_id, best.url, season=i)
