import os, time, collections, logging

log = logging.getLogger("dinoteeth.metadata")
log.setLevel(logging.DEBUG)

from metadata import Company, Person, FilmSeries, MovieMetadata, SeriesMetadata, FakeMovieMetadata, FakeSeriesMetadata

class MetadataLookup(object):
    imdb_allowed_kinds = ['movie', 'video movie', 'tv movie', 'series', 'tv series', 'tv mini series']

    def __init__(self, zodb, proxies):
        self.zodb = zodb
        self.metadata = zodb.get_mapping("metadata")
        self.people = zodb.get_mapping("people")
        self.companies = zodb.get_mapping("companies")
        self.film_series = zodb.get_mapping("film_series")
        self.imdb_api = proxies.imdb_api
        self.tmdb_api = proxies.tmdb_api
        self.tvdb_api = proxies.tvdb_api
        self.language = proxies.language
    
    def get(self, pathname):
        return self.metadata[pathname]
    
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
            elif (find == "movie" or find == "series") and kind == "tv movie":
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
                log.debug("Skipping %s (%s) because %s != %s" % (unicode(result['title']).encode("utf8"), result.get('year','<????>'), unicode(result['kind']).encode("utf8"), find))
                continue
            
            if fetch:
                self.fetch(result)
            
            log.debug("Using %s (%s) because %s could match %s" % (unicode(result['title']).encode("utf8"), result['year'], unicode(result['kind']).encode("utf8"), find))
            found.append(result)
        return found
    
    def best_guess(self, movie, fetch=False):
        # First entry in results is assumed to be the best match
        found = self.guess(movie, fetch)
        if found:
            return found[0]
        return None
    
    def best_guess_from_media_files(self, title_key, scans):
        if title_key.category != "video":
            log.debug("%s not currently supported media for metadata lookup" % title_key.category)
            return None
        kind = title_key.subcategory
        log.debug("Guessing for: %s" % scans)
        guesses = self.guess(title_key.title, year=title_key.year, find=kind)
        if not guesses:
            log.error("IMDb returned no guesses for %s???" % title_key.title)
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
        else:
            best = self.get_fake_metadata(title_key, scans)
        self.metadata[best.id] = best
        return best
    
    def get_fake_metadata(self, title_key, scans):
        kind = title_key.subcategory
        id = self.zodb.get_unique_id()
        if kind == "movie":
            metadata = FakeMovieMetadata(id, title_key, scans, self)
        else:
            metadata = FakeSeriesMetadata(id, title_key, scans, self)
        return metadata
    
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
