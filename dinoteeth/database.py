import os, collections, logging

import utils
from serializer import PickleSerializerMixin, FilePickleDict
from media import MediaScan
from metadata import Company, Person, FilmSeries, MovieMetadata, SeriesMetadata

import imdb
import tmdb3
from third_party.tvdb_api import tvdb_api, tvdb_exceptions

log = logging.getLogger("dinoteeth.database")


class MediaScanList(list):
    def get_seasons(self):
        seasons = set()
        for m in self:
            seasons.add(m.season)
        seasons = list(seasons)
        seasons.sort()
        return seasons
    
    def get_episodes(self, season_number):
        episodes = []
        for m in self:
            if m.season == season_number:
                episodes.append(m)
        episodes.sort()
        return episodes
    
    def get_total_runtime(self):
        """Return best guess for runtime of main feature, or total time
        of episodes (ignoring bonus features)
        
        @returns: (tuple) time in minutes, number of episodes
        """
        runtimes = []
        for m in self:
            if not m.is_bonus():
                runtimes.append(m.length / 60.0)
        runtimes.sort()
        # Throw out largest and smallest, replace with median
        print "get_total_runtime: %s: before=%s" % (m.title, runtimes)
        num = len(runtimes)
        if num > 4:
            median = runtimes[num/2]
            runtimes[0] = median
            runtimes[-1] = median
        print "get_total_runtime: %s: after median=%s" % (m.title, runtimes)
        return reduce(lambda a,b: a+b, runtimes), num
    
    def get_main_feature(self):
        non_bonus = []
        for m in self:
            if not m.is_bonus():
                non_bonus.append((m.length, m))
        non_bonus.sort()
        try:
            return non_bonus[0][1]
        except:
            return None

class MediaScanDatabase(PickleSerializerMixin):
    def __init__(self, **kwargs):
        PickleSerializerMixin.__init__(self, **kwargs)
        self.create()
        
    def create(self):
        self.createVersion1()
    
    def createVersion1(self):
        self.db = {}
        self.title_key_map = {}
        self.imdb_to_title_key = {}
        self.title_key_to_imdb = {}
    
    def packVersion1(self):
        return self.db, self.title_key_map, self.imdb_to_title_key, self.title_key_to_imdb
    
    def unpackVersion1(self, data):
        self.db, self.title_key_map, self.imdb_to_title_key, self.title_key_to_imdb = data
    
    def is_current(self, pathname, known_keys=None):
        if pathname in self.db:
            if known_keys is not None:
                known_keys.add(pathname)
            media_scan = self.db[pathname]
            return media_scan.is_current()
        return False
    
    def known_keys(self):
        return set(self.db.keys())
    
    def add(self, pathname, flags="", known_keys=None):
        media_scan = MediaScan(pathname, flags=flags)
        return self.add_media(media_scan, known_keys)
    
    def add_media(self, media_scan, known_keys=None):
        self.db[media_scan.pathname] = media_scan
        if known_keys is not None:
            known_keys.add(media_scan.pathname)
        key = media_scan.title_key
        if key not in self.title_key_map:
            self.title_key_map[key] = MediaScanList()
        self.title_key_map[key].append(media_scan)
        log.debug("added %s" % str(media_scan))
        return media_scan
    
    def remove(self, name):
        media_scan = self.db[name]
        del self.db[name]
        self.remove_media(media_scan)
    
    def remove_media(self, media_scan):
        title_key = media_scan.title_key
        if title_key in self.title_key_map:
            media_scan_list = self.title_key_map[title_key]
            media_scan_list.remove(media_scan)
            if len(media_scan_list) == 0:
                # If we've removed the last entry in the list for this title
                # key, remove all traces of the title key and associated
                # mappings
                del self.title_key_map[title_key]
                if title_key in self.title_key_to_imdb:
                    imdb_id = self.title_key_to_imdb[title_key]
                    del self.title_key_to_imdb[title_key]
                    del self.imdb_to_title_key[imdb_id]
    
    def get(self, name):
        return self.db[name]
    
    def get_title_key(self, name):
        media_scan = self.db[name]
        return media_scan.title_key
    
    def __iter__(self):
        for v in self.db.itervalues():
            yield v
    
    def iter_title_keys(self):
        for k,v in self.title_key_map.iteritems():
            yield k
    
    def iter_title_keys_without_imdb(self):
        for k,v in self.title_key_map.iteritems():
            if k not in self.title_key_to_imdb:
                yield k
    
    def get_all_with_title_key(self, title_key):
        return self.title_key_map.get(title_key, MediaScanList())
    
    def get_all_with_imdb_id(self, imdb_id):
        title_key = self.imdb_to_title_key[imdb_id]
        return self.get_all_with_title_key(title_key)
    
    def set_imdb_id(self, title_key, imdb_id):
        self.imdb_to_title_key[imdb_id] = title_key
        self.title_key_to_imdb[title_key] = imdb_id
    
    def get_imdb_id(self, title_key):
        return self.title_key_to_imdb[title_key]
    
    def fix_missing_metadata(self, mmdb):
        rescan = []
        for i, title_key in enumerate(self.iter_title_keys_without_imdb()):
            print "%i: missing metadata for %s" % (i, str(title_key))
            imdb_id = self.add_metadata_from_mmdb(title_key, mmdb)
            if imdb_id is None:
                rescan.append(title_key)
        self.rescan_title_keys(rescan, mmdb)
    
    def rescan_title_keys(self, rescan_list, mmdb):
        for title_key in rescan_list:
            if title_key not in self.title_key_map:
                continue
            old_media = self.title_key_map[title_key]
            for media_scan in old_media:
                self.remove_media(media_scan)
                log.info("  before reset: %s %s" % (str(media_scan.title_key), str(media_scan)))
                # perform new guessit in case guessit has been updated
                media_scan.reset()
                self.add_media(media_scan)
                log.info("  after reset: %s %s" % (str(media_scan.title_key), str(media_scan)))
    
    def add_metadata_from_mmdb(self, title_key, mmdb):
        scans = self.get_all_with_title_key(title_key)
        movie = mmdb.best_guess_from_media_scans(title_key, scans)
        if movie:
            imdb_id = movie.id
            self.set_imdb_id(title_key, imdb_id)
            return imdb_id
        return None


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
            results = self.imdb_api.search_movie(title)
            if self.use_cache:
                log.debug("*** STORING %s in search cache: " % title)
                self.search_cache[title] = results
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
            movie_obj = self.imdb_api.get_movie(imdb_id[2:])
            if self.use_cache and movie_obj:
                log.debug("*** STORING %s in movie cache: " % imdb_id)
                self.movie_obj_cache[imdb_id] = movie_obj
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


class MetadataDatabase(PickleSerializerMixin):
    def __init__(self, default_version=1):
        PickleSerializerMixin.__init__(self, default_version)
        self.create()
    
    def create(self):
        self.createVersion1()
    
    def createVersion1(self):
        self.db = {}
    
    def packVersion1(self):
        return self.db
    
    def unpackVersion1(self, data):
        self.db = data

class MovieMetadataDatabase(MetadataDatabase):
    imdb_allowed_kinds = ['movie', 'video movie', 'tv movie', 'series', 'tv series', 'tv mini series']
    
    def __init__(self, imdb_cache_dir=None, tmdb_cache_dir=None, tvdb_cache_dir=None, language="en", default_version=4):
        MetadataDatabase.__init__(self, default_version)
        self.imdb_api = IMDbFileProxy(imdb_cache_dir)
        self.tmdb_api = TMDbFileProxy(tmdb_cache_dir)
        self.tvdb_api = TVDbFileProxy(tvdb_cache_dir)
        self.language = language
    
    def __str__(self):
        lines = []
        lines.append("Media:")
        for m in sorted(self.media.values()):
            lines.append(str(m))
        lines.append("People:")
        for p in sorted(self.people.values()):
            lines.append("  %s" % safestr(p))
        lines.append("Companies:")
        for c in sorted(self.companies.values()):
            lines.append("  %s" % safestr(c))
        return "\n".join(lines)
    
    def __unicode__(self):
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
    
    def createVersion1(self):
        self.movies = {}
        self.series = {}
        self.people = {}
    
    def packVersion1(self):
        return (self.movies, self.series, self.people)
    
    def unpackVersion1(self, data):
        self.movies = data[0]
        self.series = data[1]
        self.people = data[2]

    def createVersion2(self):
        self.media = {}
        self.people = {}
        self.companies = {}

    def convertVersion1ToVersion2(self):
        self.media = self.movies
        self.media.update(self.series)
        self.companies = {}
        del self.movies
        del self.series

    def packVersion2(self):
        return (self.media, self.people, self.companies)
    
    def unpackVersion2(self, data):
        self.media = data[0]
        self.people = data[1]
        self.companies = data[2]

    def createVersion3(self):
        self.media = {}
        self.people = {}
        self.companies = {}
        self.unique_counter = -1

    def convertVersion2ToVersion3(self):
        # Just extra data, so no need to convert existing data
        pass

    def packVersion3(self):
        return (self.media, self.people, self.companies, self.unique_counter)
    
    def unpackVersion3(self, data):
        self.media = data[0]
        self.people = data[1]
        self.companies = data[2]
        self.unique_counter = data[3]

    def createVersion4(self):
        self.media = {}
        self.people = {}
        self.companies = {}
        self.film_series = {}
        self.unique_counter = -1

    def convertVersion3ToVersion4(self):
        # Just extra data, so no need to convert existing data
        pass

    def packVersion4(self):
        return (self.media, self.people, self.companies, self.film_series, self.unique_counter)
    
    def unpackVersion4(self, data):
        self.media = data[0]
        self.people = data[1]
        self.companies = data[2]
        self.film_series = data[3]
        self.unique_counter = data[4]

    def search_movie(self, title):
        if self.imdb_cache:
            results = self.imdb_cache.get_search_results(title)
            if results:
                return results
        results = self.imdb_api.search_movie(title)
        if self.imdb_cache:
            self.imdb_cache.set_search_results(title, results)
        return results

    def guess(self, title, fetch=False, year=None, find=None):
        if year:
            title = "%s (%s)" % (title, year)
        found = []
        try:
            results = self.imdb_api.search_movie(title)
        except:
            log.info("Failed looking up %s" % title)
            #return None
            raise
        for result in results:
            imdb_id = result.imdb_id
            if imdb_id is None:
                continue
            kind = result['kind']
            if kind not in self.imdb_allowed_kinds:
                log.warning("Unrecognized IMDb kind %s for %s; skipping" % (kind, imdb_id))
                continue
            elif (find == "movie" or find == "series") and kind != "tv movie":
                # TV Movies are treated as possible matches for both movies
                # and series
                pass
            elif find is not None and find not in kind:
                # Other than TV Movies, skip results different from the
                # requested kind
                #
                # IMDB seems to have at least these kinds:
                #
                # movie, tv movie, tv series, video game, video movie
                # (something like a youtube video?)
                log.debug("Skipping %s (%s) because %s != %s" % (unicode(result['title']).encode("utf8"), result['year'], unicode(result['kind']).encode("utf8"), find))
                continue
            
            if fetch:
                self.fetch(result)
            
            found.append(result)
        return found
    
    def best_guess(self, movie, fetch=False):
        # First entry in results is assumed to be the best match
        found = self.guess(movie, fetch)
        if found:
            return found[0]
        return None
    
    def best_guess_from_media_scans(self, title_key, scans):
        kind = title_key[2]
        guesses = self.guess(title_key[0], year=title_key[1], find=kind)
        if not guesses:
            log.error("IMDb returned no guesses for %s???" % title_key[0])
            return None
        total_runtime, num_episodes = scans.get_total_runtime()
        avg_runtime = total_runtime / num_episodes
        avg_scale = avg_runtime * 4 / 60 # +- 4 minutes per hour
        with_commercials = avg_runtime * 30 / 22
        commercial_scale = with_commercials * 4 / 60 # +- 4 minutes per hour
        log.debug("runtime: %f (%f with commercials if applicable)" % (avg_runtime, with_commercials))
        
        def best_loop():
            closest = 10000
            best = None
            for guess in guesses:
                movie = self.fetch(guess, store=False)
                for r in movie.runtimes:
                    log.debug("runtime: %s %s" % (movie.title.encode('utf8'), r))
                    if r == 0:
                        continue
                    if r - avg_scale < avg_runtime < r + avg_scale:
                        return movie
                    elif kind == "series":
                        # IMDb runtimes are not very accurate for series, so
                        # just accept the first match when it's a series
                        return movie
                    elif movie.is_tv() and (r - commercial_scale < with_commercials < r + commercial_scale):
                        return movie
                    else:
                        log.debug("IMDb runtimes of %s = %s; avg/w comm/total runtime = %s, %s, %s.  Skipping" % (movie.title, str(movie.runtimes), avg_runtime, with_commercials, total_runtime))
                if not best:
                    best = movie
                else:
                    diff = abs(avg_runtime - movie.runtime)
                    if diff < closest:
                        closest = diff
                        best = movie
            return best
        
        if avg_runtime > 0:
            best = best_loop()
        else:
            best = guesses[0]
        if best:
            log.info("best guess: %s, %s" % (best.title.encode('utf8'), best.runtimes))
            self.media[best.id] = best
        return best
    
    def contains_imdb_id(self, imdb_id):
        return imdb_id in self.media
    
    def fetch_imdb_id(self, imdb_id, replace=False, store=True):
        if imdb_id in self.media and not replace:
            log.debug("Already exists in local movie database")
            return self.media[imdb_id]
        imdb_obj = self.imdb_api.get_movie(imdb_id)
        if imdb_obj['kind'] in ['movie', 'video movie', 'tv movie']:
            tmdb_obj = self.tmdb_api.get_imdb_id(imdb_id)
            media = MovieMetadata(imdb_obj, tmdb_obj, self)
        elif imdb_obj['kind'] in ['series', 'tv series', 'tv mini series']:
            tvdb_obj = self.tvdb_api.get_imdb_id(imdb_id)
            media = SeriesMetadata(imdb_obj, tvdb_obj, self)
        else:
            # It's a video game or something else; skip it
            log.error("Unhandled IMDb type '%s' for %s" % (imdb_obj['kind'], imdb_id))
            return
        if store:
            self.media[imdb_id] = media
        print (u"%s: %s -> %s" % (imdb_obj['title'], imdb_obj['kind'], media.media_category)).encode('utf8')
        return media
    
    def fetch(self, result, store=True):
        imdb_id = result.imdb_id
        return self.fetch_imdb_id(imdb_id, store=store)
    
    def get_unique_id(self):
        id = self.unique_counter
        self.unique_counter -= 1
        return id
    
    def get_person(self, person_obj):
        id = person_obj.personID
        if id in self.people:
            person = self.people[id]
        else:
            person = Person(person_obj)
            self.people[id] = person
        return person
    
    def prune_people(self, imdb_obj, match="", max=25):
        """Create list of Person objects where the notes field of the imdb
        Person object matches the criteria.
        
        Side effect: removes matched IMDb Person objects from input list
        """
        persons = []
        unmatched = imdb_obj[:]
        for p in unmatched:
            if match in p.notes:
                persons.append(self.get_person(p))
                imdb_obj.remove(p)
                if len(persons) >= max:
                    break
        return persons
        
    def get_company(self, company_obj):
        id = company_obj.companyID
        if id in self.companies:
            company = self.companies[id]
        else:
            company = Company(company_obj)
            self.companies[id] = company
        return company
    
    def get_company_by_name(self, company_name):
        for id, company in self.companies.iteritems():
            if company.name == company_name:
                return self.companies[id]
        id = self.get_unique_id()
        company = Company(None, id, company_name)
        self.companies[id] = company
        return company
    
    def prune_companies(self, imdb_obj, max=5):
        """Create list of Company objects where the notes field of the imdb
        Person object matches the criteria.
        
        Side effect: removes matched IMDb Person objects from input list
        """
        companies = []
        unmatched = imdb_obj[:]
        for p in unmatched:
            companies.append(self.get_company(p))
            imdb_obj.remove(p)
            if len(companies) >= max:
                break
        return companies
        
    def get_film_series(self, tmdb_film_series):
        id = tmdb_film_series['id']
        if id in self.film_series:
            film_series = self.film_series[id]
        else:
            film_series = FilmSeries(tmdb_film_series)
            self.film_series[id] = film_series
        return film_series
    
    def get_film_series_by_name(self, series_name):
        for id, film_series in self.film_series.iteritems():
            if film_series.name == series_name:
                return self.film_series[id]
        id = self.get_unique_id()
        film_series = FilmSeries(None, id, film_series)
        self.film_series[id] = film_series
        return film_series
    
    def fetch_poster(self, imdb_id, artwork_loader):
        if imdb_id in self.media:
            media = self.media[imdb_id]
            if media.media_category == 'series':
                loaders = ['tvdb', 'tmdb']
            else:
                loaders = ['tmdb', 'tvdb']
            
            for loader in loaders:
                try:
                    if loader == 'tvdb':
                        return self.fetch_poster_tvdb(imdb_id, media, artwork_loader)
                    elif loader == 'tmdb':
                        return self.fetch_poster_tmdb(imdb_id, artwork_loader)
                except KeyError:
                    pass
            return None
        else:
            raise KeyError("IMDb title %s not in local database" % imdb_id)
    
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
    
    def fetch_poster_tmdb(self, imdb_id, artwork_loader):
        tfilm = self.tmdb_api.get_imdb_id(imdb_id)
        if tfilm is None:
            raise KeyError
        found = tfilm.get_best_poster('w342', language=self.language)
        if found:
            log.debug("best poster: %s" % found)
            artwork_loader.save_poster_from_url(imdb_id, found)
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

    def fetch_poster_tvdb(self, imdb_id, media, artwork_loader):
        show = self.tvdb_api.get_imdb_id(imdb_id)
        if not show:
            log.debug("No tvdb entry for %s: %s" % (imdb_id, unicode(media.title).encode('utf8')))
            return
        self.fetch_poster_tvdb_series(show, imdb_id, media, artwork_loader)
        self.fetch_poster_tvdb_seasons(show, imdb_id, media, artwork_loader)
        
    def fetch_poster_tvdb_series(self, show, imdb_id, media, artwork_loader):
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
            artwork_loader.save_poster_from_url(imdb_id, best.url)
        else:
            log.debug("No poster for %s" % unicode(media.title).encode('utf8'))
        
    def fetch_poster_tvdb_seasons(self, show, imdb_id, media, artwork_loader):
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
            artwork_loader.save_poster_from_url(imdb_id, best.url, season=i)

    def lambdaify(self, criteria):
        if isinstance(criteria, collections.Callable):
            return criteria
        if isinstance(criteria, collections.Iterable) and not isinstance(criteria, basestring):
            return lambda a: a in criteria
        if criteria is not None:
            return lambda a: a == criteria
        return lambda a: True

    def get(self, imdb_id):
        return self.media[imdb_id]
    
    def remove(self, imdb_id):
        del self.media[imdb_id]

    def get_media_by(self, media_categories, credit, criteria=None):
        """Get a lists of movies given the category and search parameters

        Criteria can be a string, an iterable, or a function.
        """
        results = set()
        log.debug("get_media_by: cat=%s credit=%s criteria=%s" % (media_categories, credit, str(criteria)))
        criteria = self.lambdaify(criteria)
        for m in self.media.values():
            if media_categories is None or m.media_category in media_categories:
                if m.match(credit, criteria):
                    log.debug("matched %s" % m.title)
                    results.add(m)
        order = []
        for m in results:
            sort_key = m.sort_key(credit)
            order.append((sort_key, m))
        order.sort()
        return [item[1] for item in order]

    def get_credit_entries(self, media_categories, credit, criteria=None):
        """Get a lists of movies given the category and search parameters

        Criteria can be a string, an iterable, or a function.
        """
        results = set()
        log.debug("get_credit_entries: cat=%s credit=%s criteria=%s" % (media_categories, credit, str(criteria)))
        criteria = self.lambdaify(criteria)
        for m in self.media.values():
#            print type(m), media_categories, m.media_category
            if media_categories is None or m.media_category in media_categories:
                log.debug("matched media category %s!" % m.media_category)
                if m.match(credit, criteria):
                    log.debug("matched %s" % m.title)
                    results.update(m.iter_items_of(credit))
        return list(results)
