#!/usr/bin/env python
"""
Get TMDB/IMDB metadata for movies in the database
"""

import os, re, time, collections, logging

from ..metadata import MetadataLoader
from metadata import *
from proxies import Proxies, TMDbMovieBestPosterFromIdTask

log = logging.getLogger("dinoteeth.home_theater")


class HomeTheaterMetadataLoader(MetadataLoader):
    imdb_allowed_kinds = ['movie', 'video movie', 'tv movie', 'series', 'tv series', 'tv mini series']
    proxies = None
    ignored_imdb_ids = set()
    
    def init_proxies(self, settings):
        if self.__class__.proxies is not None:
            return
        self.__class__.proxies = Proxies(settings)

    def search(self, title_key):
        title = title_key.title
        subcat = title_key.subcategory
        if title_key.year:
            title = "%s (%s)" % (title, title_key.year)
        found = []
        try:
            results = self.proxies.imdb_api.search_movie(title)
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
            elif (subcat == "movie" or subcat == "series") and kind == "tv movie":
                # TV Movies are treated as possible matches for both movies
                # and series
                pass
            elif subcat is not None and subcat not in kind:
                # Other than TV Movies, skip results different from the
                # requested kind
                #
                # IMDB seems to have at least these kinds:
                #
                # movie, tv movie, tv series, video game, video movie
                # (something like a youtube video?)
                log.debug("Skipping %s (%s) because %s != %s" % (unicode(result['title']).encode("utf8"), result.get('year','<????>'), unicode(result['kind']).encode("utf8"), subcat))
                continue
            
#            log.debug("Using %s (%s) because %s could match %s" % (unicode(result['title']).encode("utf8"), result.get('year', None), unicode(result['kind']).encode("utf8"), subcat))
            found.append(result)
        guesses = self.prioritize_search(title_key, found)
        for result in guesses:
            log.debug("Using %s (%s) because %s could match %s" % (unicode(result['title']).encode("utf8"), result.get('year', None), unicode(result['kind']).encode("utf8"), subcat))
        return guesses
    
    def prioritize_search(self, title_key, guesses):
        title = title_key.title.lower()
        exact_matches = []
        others = []
        for result in guesses:
            t = unicode(result['title']).encode("utf8").lower()
            if t == title:
                exact_matches.append(result)
                continue
            elif t.endswith(")"):
                # Handle titles with imdbIndex at the end, e.g. "Ghost Town (I)"
                match = re.match("(.+?)( *\([ivx]+\))", t)
                if match:
                    t = match.group(1)
                    if t == title:
                        exact_matches.append(result)
                        continue
            others.append(result)
        exact_matches.extend(others)
        return exact_matches
    
    def get_metadata_by_id(self, imdb_id):
        imdb_obj = self.proxies.imdb_api.get_movie(imdb_id)
        if imdb_obj['kind'] in ['movie', 'video movie', 'tv movie']:
            tmdb_obj = self.proxies.tmdb_api.get_imdb_id(imdb_id)
            metadata = MovieMetadata(imdb_obj, tmdb_obj)
        elif imdb_obj['kind'] in ['series', 'tv series', 'tv mini series']:
            tvdb_obj = self.proxies.tvdb_api.get_imdb_id(imdb_id)
            metadata = SeriesMetadata(imdb_obj, tvdb_obj)
        else:
            # It's a video game or something else; skip it
            log.error("Unhandled IMDb type '%s' for %s" % (imdb_obj['kind'], imdb_id))
            return
        print (u"%s: %s -> %s" % (imdb_obj['title'], imdb_obj['kind'], metadata.media_subcategory)).encode('utf8')
        return metadata
    
    def get_metadata(self, result):
        imdb_id = result.imdb_id
        return self.get_metadata_by_id(imdb_id)
    
    def get_fake_metadata(self, title_key, scans):
        kind = title_key.subcategory
        id = None
        if kind == "movie":
            metadata = FakeMovieMetadata(id, title_key, scans)
        else:
            metadata = FakeSeriesMetadata(id, title_key, scans)
        return metadata
    
    def get_basic_metadata(self, title_key, result):
        id = result.imdb_id
        if result['kind'] in ['movie', 'video movie', 'tv movie']:
            metadata = FakeMovieMetadata(id, title_key, None)
        elif result['kind'] in ['series', 'tv series', 'tv mini series']:
            metadata = FakeSeriesMetadata(id, title_key, None)
        else:
            # It's a video game or something else; skip it
            log.error("Unhandled IMDb type '%s' for %s" % (result['kind'], imdb_id))
            metadata = FakeMovieMetadata(id, title_key)
        return metadata
    
    def best_loop(self, guesses, kind, total_runtime, avg_runtime):
        avg_scale = avg_runtime * 4 / 60 # +- 4 minutes per hour
        with_commercials = avg_runtime * 30 / 22
        commercial_scale = with_commercials * 4 / 60 # +- 4 minutes per hour
        log.debug("runtime: %f (%f with commercials if applicable)" % (avg_runtime, with_commercials))

        closest = 10000
        best = None
        for guess in guesses[:5]: # Only check the first few guesses
            log.debug(">>>>> checking: %s" % guess.imdb_id)
            summary = self.proxies.tmdb_api.get_imdb_id(guess.imdb_id)
            if summary is not None and summary["runtime"] > 0:
                title = summary["title"]
                runtimes = [summary["runtime"]]
                movie = None
                print "using tmdb: %s" % runtimes
            else:
                try:
                    movie = self.get_metadata(guess)
                except:
                    print "failed loading imdb; probably in production or rumored movie"
                if movie is None or kind != movie.media_subcategory:
                    continue
                title = movie.title
                runtimes = movie.runtimes
                print "using imdb: %s" % runtimes
            if not runtimes:
                # No valid runtimes probably means it's an in-production movie
                continue
            
            for r in runtimes:
                log.debug("runtime: %s %s" % (title.encode('utf8'), r))
                if r == 0:
                    continue
                if kind == "series":
                    # IMDb runtimes are not very accurate for series, so
                    # just accept the first match when it's a series
                    return movie
                elif r - avg_scale < avg_runtime < r + avg_scale:
                    break
                elif movie is not None and movie.is_tv() and (r - commercial_scale < with_commercials < r + commercial_scale):
                    break
                else:
                    log.debug("IMDb runtimes of %s = %s; avg/w comm/total runtime = %s, %s, %s.  Skipping" % (title, str(runtimes), avg_runtime, with_commercials, total_runtime))
            if not best:
                best = guess.imdb_id
                closest = abs(avg_runtime - runtimes[0])
            else:
                diff = abs(avg_runtime - runtimes[0])
                if diff < closest:
                    closest = diff
                    best = guess.imdb_id
        if best is not None:
            best = self.get_metadata_by_id(best)
        return best
        
    def best_guess(self, title_key, scans):
        kind = title_key.subcategory
        log.debug("Guessing for: %s" % scans)
        guesses = self.search(title_key)
        if not guesses:
            log.error("IMDb returned no guesses for %s???" % title_key.title)
        total_runtime, num_episodes = scans.get_total_runtime()
        avg_runtime = total_runtime / num_episodes
        
        log.debug("%d guesses for '%s' %s" % (len(guesses), kind, title_key.title))
        if avg_runtime > 0:
            best = self.best_loop(guesses, kind, total_runtime, avg_runtime)
        elif len(guesses) > 0:
            best = self.get_metadata(guesses[0])
        if best:
            log.debug("best guess: %s, %s" % (best.title.encode('utf8'), best.runtimes))
        else:
            best = self.get_fake_metadata(title_key, scans)
        return best
    
    def fetch_posters(self, item):
        if item.id in self.ignored_imdb_ids:
            log.debug("%s ignored; not attempting to load posters" % item.id)
            return None
        if item.media_subcategory == 'series':
            loaders = [self.fetch_poster_tvdb, self.fetch_poster_tmdb]
        else:
            loaders = [self.fetch_poster_tmdb, self.fetch_poster_tvdb]
        
        no_posters = 0
        for loader in loaders:
            try:
                if loader(item):
                    return
                no_posters += 1
            except KeyError:
                no_posters += 1
            except Exception, e:
                import traceback
                traceback.print_exc()
                log.error("Error loading poster for %s: %s" % (item.id, e))
                pass
        if no_posters == len(loaders):
            log.error("No poster for %s: skipping further attempts" % item.id)
            self.ignored_imdb_ids.add(item.id)
        return None
    
    # TMDb specific poster lookup
    def tmdb_poster_info(self, poster):
        urls = {}
        for key, url in poster.items():
            print "key: %s, url %s" % (key, url)
            if url.startswith("http") and "/t/p/" in url:
                _, imginfo = url.split("/t/p/")
                size, filename = imginfo.split("/")
                if size.startswith("w") or size == "original":
                    urls[size] = url
                log.debug("%s: %s" % (size, url))
        return urls
    
    def fetch_poster_tmdb(self, item):
        tfilm = self.proxies.tmdb_api.get_imdb_id(item.id)
        if tfilm is None:
            raise KeyError
        tfilm.discover_images()
        found = tfilm.get_best_poster_url('w342')
        if found:
            log.debug("best tmdb poster: %s" % found)
            data = self.proxies.tmdb_api.load_url(found)
            self.save_poster(item, found, data)
            return True
        else:
            log.debug("No poster for %s" % unicode(tfilm).encode('utf8'))
        return False

    def fetch_poster_tvdb(self, item):
        show = self.proxies.tvdb_api.get_imdb_id(item.id)
        if not show:
            raise KeyError
        main, season_map = self.proxies.tvdb_api.fetch_poster_urls(show)
        if main:
            log.debug("best tvdb poster: %s" % main)
            data = self.proxies.tvdb_api.load_url(main)
            self.save_poster(item, main, data)
            for season, url in season_map.iteritems():
                log.debug("best season %d tvdb poster: %s" % (season, url))
                data = self.proxies.tvdb_api.load_url(url)
                suffix = self.get_poster_suffix(season=season)
                self.save_poster(item, url, data, suffix=suffix)
        return main
    
    def get_poster_suffix(self, **kwargs):
        if 'season' in kwargs and kwargs['season'] is not None:
            return "-s%02d" % kwargs['season']
        return ""
    
    def get_poster_background_task(self, metadata):
        task = TMDbMovieBestPosterFromIdTask(self.proxies.tmdb_api, metadata, self)
        return task

MetadataLoader.register("video", "*", HomeTheaterMetadataLoader)
