import os, collections, logging

from utils import iter_dir
from serializer import PickleSerializerMixin, FilePickleDict
from media import MediaScan
from metadata import Company, Person, FilmSeries, MovieMetadata, SeriesMetadata

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
    
    def get_bonus(self, season_number=-1):
        bonus = []
        for m in self:
            if (season_number < 0 or m.season == season_number) and m.is_bonus():
                bonus.append(m)
        bonus.sort()
        return bonus
    
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
        
        # Handle pathological case
        if len(runtimes) == 0:
            return (0, 1)
        
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
    
    def remove(self, name, mmdb):
        media_scan = self.db[name]
        del self.db[name]
        self.remove_media(media_scan, mmdb)
    
    def remove_media(self, media_scan, mmdb):
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
                    self.imdb_to_title_key[imdb_id].discard(title_key)
                    if len(self.imdb_to_title_key[imdb_id]) == 0:
                        del self.imdb_to_title_key[imdb_id]
                    mmdb.remove(imdb_id)
    
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
        m = MediaScanList()
        for title_key in self.imdb_to_title_key[imdb_id]:
            m.extend(self.get_all_with_title_key(title_key))
        return m
    
    def set_imdb_id(self, title_key, imdb_id):
        # Multiple title keys may share the same imdb_id! E.g.  "TopGear" and
        # "Top Gear" mapping to the same show.
        if imdb_id not in self.imdb_to_title_key:
            self.imdb_to_title_key[imdb_id] = set()
        self.imdb_to_title_key[imdb_id].add(title_key)
        self.title_key_to_imdb[title_key] = imdb_id
    
    def get_imdb_id(self, title_key):
        return self.title_key_to_imdb[title_key]
    
    def fix_missing_imdb_id(self, mmdb):
        rescan = set()
        for i, title_key in enumerate(self.iter_title_keys_without_imdb()):
            print "%i: missing metadata for %s" % (i, str(title_key))
            imdb_id = self.add_imdb_id(title_key, mmdb)
            if imdb_id is None:
                rescan.add(title_key)
        return self.rescan_title_keys(rescan, mmdb)
    
    def rescan_title_keys(self, rescan_list, mmdb):
        valid_title_keys = set()
        for title_key in rescan_list:
            if title_key not in self.title_key_map:
                continue
            valid_title_keys.add(title_key)
            old_media = self.title_key_map[title_key]
            for media_scan in old_media:
                self.remove_media(media_scan, mmdb)
                log.info("  before reset: %s %s" % (str(media_scan.title_key), str(media_scan)))
                # perform new guessit in case guessit has been updated
                media_scan.reset()
                self.add_media(media_scan)
                log.info("  after reset: %s %s" % (str(media_scan.title_key), str(media_scan)))
        return valid_title_keys
    
    def add_imdb_id(self, title_key, mmdb):
        scans = self.get_all_with_title_key(title_key)
        movie = mmdb.best_guess_from_media_scans(title_key, scans)
        if movie:
            imdb_id = movie.id
            self.set_imdb_id(title_key, imdb_id)
            return imdb_id
        return None
    
    def scan_files(self, path_iterable, flags, known_keys=None):
        """Scan files from an iterable object and add them to the database
        """
        for pathname in path_iterable:
            if not self.is_current(pathname, known_keys=known_keys):
                media_scan = self.add(pathname, flags, known_keys=known_keys)
                log.debug("added: %s" % self.get(media_scan.pathname))
    
    def scan_dirs(self, media_path_dict, valid_extensions=None):
        stored_keys = self.known_keys()
        current_keys = set()
        for path, flags in media_path_dict.iteritems():
            print "Parsing path %s" % path
            dir_iterator = iter_dir(path, valid_extensions)
            self.scan_files(dir_iterator, flags, current_keys)
        self.saveStateToFile()
        removed_keys = stored_keys - current_keys
        new_keys = current_keys - stored_keys
        return removed_keys, new_keys
    
    def update_metadata(self, media_path_dict, mmdb, artwork_loader, valid_extensions=None):
        removed_keys, new_keys = self.scan_dirs(media_path_dict, valid_extensions)
        if removed_keys:
            print "Found files that have been removed! %s" % str(removed_keys)
            self.remove_metadata(removed_keys, mmdb)
        if new_keys:
            print "Found files that have been added! %s" % str(new_keys)
            self.add_metadata(new_keys, mmdb, artwork_loader)
        missing_title_keys = self.fix_missing_imdb_id(mmdb)
        self.update_new_title_keys_metadata(new_keys, missing_title_keys, mmdb)
        self.saveStateToFile()
        mmdb.saveStateToFile()
    
    def remove_metadata(self, removed_keys, mmdb):
        for i, key in enumerate(removed_keys):
            title_key = self.get_title_key(key)
            try:
                imdb_id = self.get_imdb_id(title_key)
            except KeyError:
                log.info("%d: orphaned title key %s has no imdb_id" % (i, str(title_key)))
                continue
            print "%d: removing imdb=%s %s" % (i, imdb_id, str(title_key))
            self.remove(key, mmdb)
    
    def add_metadata(self, new_keys, mmdb, artwork_loader):
        count = len(new_keys)
        for i, key in enumerate(new_keys):
            title_key = self.get_title_key(key)
            try:
                imdb_id = self.get_imdb_id(title_key)
                print "%d/%d: imdb=%s %s" % (i, count, imdb_id, str(title_key))
            except KeyError:
                print "%d/%d: imdb=NOT FOUND %s" % (i, count, str(title_key))
                imdb_id = self.add_imdb_id(title_key, mmdb)
                for j, media in enumerate(self.get_all_with_title_key(title_key)):
                    log.info("  media #%d: %s" % (j, str(media)))
            if imdb_id:
                if not mmdb.contains_imdb_id(imdb_id):
                    log.debug("Loading imdb_id %s" % imdb_id)
                    mmdb.fetch_imdb_id(imdb_id)

    def update_new_title_keys_metadata(self, new_keys, missing_title_keys, mmdb):
        new_title_keys = set(missing_title_keys)
        for key in new_keys:
            media_scan = self.db[key]
            new_title_keys.add(media_scan.title_key)
        log.debug("title keys with new files: %s" % str(new_title_keys))
        for title_key in new_title_keys:
            media_scans = self.get_all_with_title_key(title_key)
            imdb_id = self.get_imdb_id(title_key)
            metadata = mmdb.get(imdb_id)
            metadata.update_with_media_scans(media_scans)


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
    
    def __init__(self, proxies, default_version=4):
        MetadataDatabase.__init__(self, default_version)
        self.imdb_api = proxies.imdb_api
        self.tmdb_api = proxies.tmdb_api
        self.tvdb_api = proxies.tvdb_api
        self.language = proxies.language
    
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
            best = self.fetch(guesses[0], store=False)
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
                    results.add(m)
        order = []
        for m in results:
            sort_key = m.sort_key(credit)
            order.append((sort_key, m))
        order.sort()
        log.debug("sort key: %s; sorted: %s" % (credit, str([(item[0], item[1].title) for item in order])))
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
