import os, collections, logging

from utils import iter_dir
from media import MediaScan
from metadata import Company, Person, FilmSeries, MovieMetadata, SeriesMetadata

log = logging.getLogger("dinoteeth.database")
log.setLevel(logging.DEBUG)

from ZODB import DB, FileStorage
import transaction
from persistent.mapping import PersistentMapping


class DBFacade(object):
    def __init__(self, path):
        self.storage = FileStorage.FileStorage(path)
        self.db = DB(self.storage)
        self.connection = self.db.open()
        self.dbroot = self.connection.root()
    
    def get_unique_id(self):
        id = self.get_value("unique_counter", 0)
        id -= 1
        self.set_value("unique_counter", id)
        return id
    
    def add(self, name, obj):
        self.dbroot[name] = obj
    
    def get_mapping(self, name, clear=False):
        if name not in self.dbroot:
            self.dbroot[name] = PersistentMapping()
        if clear:
            self.dbroot[name].clear()
        return self.dbroot[name]
    
    def get_value(self, name, initial):
        if name not in self.dbroot:
            self.dbroot[name] = initial
        return self.dbroot[name]
    
    def set_value(self, name, value):
        self.dbroot[name] = value
    
    def add(self, name, obj):
        self.dbroot[name] = obj
    
    def commit(self):
        transaction.commit()
    
    def rollback(self):
        transaction.rollback()
    
    def abort(self):
        transaction.abort()
    
    def pack(self):
        self.db.pack()

    def close(self):
        self.connection.close()
        self.db.close()
        self.storage.close()


class MediaScanList(list):
    def __init__(self, parent=None, filter_callable=None, *args, **kwargs):
        list.__init__(self, *args, **kwargs)
        self.parent = parent
        if filter_callable is None:
            filter_callable = lambda x: True
        self.filter_callable = filter_callable
        
    def __str__(self):
        lines = []
        for scan in self:
            lines.append("scan -> %s" % scan.pathname)
            lines.append("  title_key: %s" % str(scan.title_key))
            lines.append("  guess: %s" % scan.guess)
            lines.append("  metadata: %s" % scan.metadata)
        return "\n".join(lines)
        
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
    
    def get_unique_metadata(self):
        s = set()
        for item in self:
            s.add(item.metadata)
        return s
    
    def get_unique_metadata_with_value(self, accessor):
        s = dict()
        for item in self:
            value = accessor(item)
            if item.metadata not in s or value > s[item.metadata]:
                s[item.metadata] = value
        return s
    
    def filter(self, criteria):
        filtered = MediaScanList(parent=self, filter_callable=criteria)
        return filtered
    
    def __iter__(self):
        if self.parent is None:
            index = 0
            while True:
                try:
                    item = self[index]
                    if self.filter_callable(item):
                        yield item
                except IndexError:
                    raise StopIteration
                index += 1
        else:
            for item in self.parent:
                if self.filter_callable(item):
                    yield item
    
    def __len__(self):
        if self.parent is None:
            return list.__len__(self)
        else:
            count = 0
            for item in self:
                count += 1
            return count


class NewDatabase(object):
    imdb_allowed_kinds = ['movie', 'video movie', 'tv movie', 'series', 'tv series', 'tv mini series']

    def __init__(self, zodb, proxies):
        self.zodb = zodb
        self.metadata = zodb.get_mapping("metadata")
        self.title_key_to_metadata = zodb.get_mapping("title_key_to_metadata")
        self.zodb_title_key_map = zodb.get_mapping("title_key_map")
        self.people = zodb.get_mapping("people")
        self.companies = zodb.get_mapping("companies")
        self.film_series = zodb.get_mapping("film_series")
        self.imdb_api = proxies.imdb_api
        self.tmdb_api = proxies.tmdb_api
        self.tvdb_api = proxies.tvdb_api
        self.language = proxies.language
    
    def pack(self):
        self.zodb.pack()
    
    def get_scans(self):
        s = self.zodb.get_mapping("scans")
        return s
    
    scans = property(get_scans)
    
    def get_all(self):
        scans = MediaScanList()
        scans.extend(self.scans.values())
        return scans
    
    def get(self, pathname):
        return self.scans[pathname]
    
    def get_metadata(self, imdb_id):
        if self.contains_imdb_id(imdb_id):
            return self.metadata[imdb_id]
        return None
    
    def add(self, pathname, flags=""):
        media_scan = MediaScan(pathname, flags=flags)
        self.scans[media_scan.pathname] = media_scan
    
    def change_metadata(self, media_scans, imdb_id):
        metadata = self.fetch_imdb_id(imdb_id)
        
        # Find all title keys referenced by the scans
        title_keys = set()
        for scan in media_scans:
            title_keys.add(scan.title_key)
        
        # Reset title key lookup to use new metadata
        for title_key in title_keys:
            self.title_key_to_metadata[title_key] = metadata
            scans = self.title_key_map[title_key]
            for scan in scans:
                log.debug("Changing metadata for %s" % scan.pathname)
                scan.metadata = metadata
                metadata.update_with_media_scans(scans)
        transaction.commit()
    
    def is_current(self, pathname, found_keys=None):
        if pathname in self.scans:
            if found_keys is not None:
                found_keys.add(pathname)
            media_scan = self.scans[pathname]
            return media_scan.is_current()
        return False
    
    def scan_files(self, path_iterable, flags, found_keys=None):
        """Scan files from an iterable object and add them to the database
        """
        for pathname in path_iterable:
            if not self.is_current(pathname, found_keys=found_keys):
                media_scan = self.add(pathname, flags)
#                log.debug("added: %s" % self.get(media_scan.pathname))
                log.debug("added: %s" % media_scan)
        
    def scan_dirs(self, media_path_dict, valid_extensions=None):
        stored_keys = set(self.scans.keys())
        current_keys = set()
        for path, flags in media_path_dict.iteritems():
            print "Parsing path %s" % path
            dir_iterator = iter_dir(path, valid_extensions)
            self.scan_files(dir_iterator, flags, current_keys)
        removed_keys = stored_keys - current_keys
        for key in removed_keys:
            print "Removing %s" % key
            del self.scans[key]
        self.create_title_key_map()
    
    def update_metadata(self, media_path_dict, valid_extensions=None):
        self.scan_dirs(media_path_dict, valid_extensions)
        transaction.commit()
        self.update_all()
        transaction.commit()
    
    def create_title_key_map(self):
        t = self.zodb.get_mapping("title_key_map", clear=True)
        for path, scan in self.scans.iteritems():
            key = scan.title_key
            if key not in t:
                t[key] = list()
            t[key].append(scan)
    
    def get_title_key_map(self):
        t = self.zodb.get_mapping("title_key_map")
        if not t:
            self.create_title_key_map()
            transaction.commit()
        return t
    
    title_key_map = property(get_title_key_map)
    
    def iter_title_key_map(self):
        for t, scans in self.title_key_map.iteritems():
            scans = MediaScanList(scans)
            yield t, scans
    
    def update_all(self):
        t = self.zodb.get_mapping("title_key_to_metadata")
        for title_key, scans in self.iter_title_key_map():
            metadata = t.get(title_key, None)
            if metadata is None:
                metadata = self.best_guess_from_media_scans(title_key, scans)
                self.title_key_to_metadata[title_key] = metadata
            for scan in scans:
                scan.metadata = metadata
            metadata.update_with_media_scans(scans)
        transaction.savepoint()
    
    def title_keys_with_metadata(self):
        t = self.zodb.get_mapping("title_key_to_metadata")
        known_keys = set(t.keys())
        current_keys = set(self.title_key_map.keys())
        valid_keys = current_keys.intersection(known_keys)
        for key in valid_keys:
            yield key, t[key]

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
            self.metadata[best.id] = best
            transaction.commit()
        return best
    
    def contains_imdb_id(self, imdb_id):
        return imdb_id in self.metadata
    
    def fetch_imdb_id(self, imdb_id, replace=False, store=True):
        if imdb_id in self.metadata and not replace:
            log.debug("Already exists in local movie database")
            return self.metadata[imdb_id]
        imdb_obj = self.imdb_api.get_movie(imdb_id)
        if imdb_obj['kind'] in ['movie', 'video movie', 'tv movie']:
            tmdb_obj = self.tmdb_api.get_imdb_id(imdb_id)
            metadata = MovieMetadata(imdb_obj, tmdb_obj, self)
        elif imdb_obj['kind'] in ['series', 'tv series', 'tv mini series']:
            tvdb_obj = self.tvdb_api.get_imdb_id(imdb_id)
            metadata = SeriesMetadata(imdb_obj, tvdb_obj, self)
        else:
            # It's a video game or something else; skip it
            log.error("Unhandled IMDb type '%s' for %s" % (imdb_obj['kind'], imdb_id))
            return
        if store:
            self.metadata[imdb_id] = metadata
            transaction.commit()
        print (u"%s: %s -> %s" % (imdb_obj['title'], imdb_obj['kind'], metadata.media_category)).encode('utf8')
        return metadata
    
    def fetch(self, result, store=True):
        imdb_id = result.imdb_id
        return self.fetch_imdb_id(imdb_id, store=store)
    
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
        id = self.zodb.get_unique_id()
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
        id = self.zodb.get_unique_id()
        film_series = FilmSeries(None, id, film_series)
        self.film_series[id] = film_series
        return film_series
