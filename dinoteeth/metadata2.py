#!/usr/bin/env python
"""
Get TMDB/IMDB metadata for movies in the database
"""

import os, os.path, sys, glob, urllib

from PIL import Image
import imdb
import tempfile

import third_party.themoviedb.tmdb as tmdb
from serializer import PickleSerializerMixin


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

def safestr(s):
    if isinstance(s, basestring):
        return s.encode('ascii', "replace")
    return s

def safeprint(s):
    if isinstance(s, basestring):
        return s.encode('utf-8')
    return s

def printdict(d, indent=""):
    for k in sorted(d.keys()):
        v = d[k]
        if isinstance(v, dict):
            print "%s%s" % (indent, safeprint(k))
            printdict(v, indent="%s    %s:" % (indent, k))
        else:
            try:
                print "%s%s: %s" % (indent, k, safeprint(v))
            except UnicodeDecodeError:
                print "%s%s: unicode probs" % (indent, k)


class Person(object):
    def __init__(self, person_obj):
        self.id = person_obj.personID
        self.name, self.surname = self.get_name(person_obj['canonical name'])
    
    def __cmp__(self, other):
        def sort_key(p):
            if p.surname:
                return [p.surname.lower(), p.name.lower()]
            return [p.name.lower(), ""]
        return cmp(sort_key(self), sort_key(other))
    
    def __str__(self):
        return safestr("%s %s" % (self.name, self.surname))
    
    def __unicode__(self):
        return u"%s %s" % (self.name, self.surname)
    
    def get_name(self, name):
        sname = name.split(u', ')
        if len(sname) == 2:
            return sname[1], sname[0]
        return sname[0], ""


class BaseMetadata(object):
    def get_country_list(self, imdb_obj, key, country, skip=None):
        if not imdb_obj.has_key(key): # Note: key in imdb_obj fails; must use has_key
            return ""
        default = ""
        values = imdb_obj[key]
#        print "get_country_list[%s]: %s" % (key, str(values))
        for value in values:
            if ":" in value:
                c, v = value.split(":", 1)
                if c == country:
                    if skip and skip in v:
                        continue
                    if "::" in v:
                        v, _ = v.split("::", 1)
                    return v
            else:
                default = value
        return default
    
    def get_people_obj(self, imdb_obj, key):
        if not imdb_obj.has_key(key):
            return []
        people_obj = imdb_obj[key]
#        print "get_people_obj[%s]: %s" % (key, str(people_obj))
        return list(people_obj)
    
    def get_title(self, imdb_obj, country):
        best = imdb_obj['title']
        if imdb_obj.has_key('akas'):
            for aka in imdb_obj['akas']:
                if "::" in aka:
                    title, note = aka.split("::")
                    if "imdb display title" in note:
                        # Only allow official display titles
#                        print safeprint(title)
                        for part in note.split(","):
#                            print "  %s" % part
                            if country in part:
                                best = title
        return best

class MovieMetadata(BaseMetadata):
    country = "USA"
    
    def __init__(self, movie_obj, db):
        self.id = movie_obj.movieID
        self.title = self.get_title(movie_obj, self.country)
        self.year = movie_obj['year']
        self.title_index = movie_obj.get('imdbIndex', "")
        self.certificate = self.get_country_list(movie_obj, 'certificates', self.country, skip="TV rating")
        self.plot = movie_obj.get('plot outline', "")
        self.genres = movie_obj.get('genres', list())
        self.rating = movie_obj.get('rating', "")
        self.votes = movie_obj.get('votes', "")
        self.runtime = self.get_country_list(movie_obj, 'runtimes', self.country)
        
        directors = self.get_people_obj(movie_obj, 'director')
        self.directors = db.prune_people(directors)
        
        producers = self.get_people_obj(movie_obj, 'producer')
        self.executive_producers = db.prune_people(producers, 'executive producer')
        self.producers = db.prune_people(producers)
        
        writers = self.get_people_obj(movie_obj, 'writer')
        self.novel_writers = db.prune_people(writers, 'novel')
        self.screenplay_writers = db.prune_people(writers, 'screenplay')
        self.story_writers = db.prune_people(writers, 'story')
        self.writers = db.prune_people(writers)
        
        music = self.get_people_obj(movie_obj, 'original music')
        self.music = db.prune_people(music)
        
        cast = self.get_people_obj(movie_obj, 'cast')
        self.cast = db.prune_people(cast)
    
    def __cmp__(self, other):
        return cmp([self.title, self.year, self.title_index],
                   [other.title, other.year, other.title_index])
    
    def __str__(self):
        lines = []
        lines.append("%s %s %s %s" % (self.id, self.title, self.year, self.title_index))
        lines.append("  %s %smin rating=%s, %s votes" % (self.certificate, self.runtime, self.rating, self.votes))
        lines.append("  %s" % (", ".join(self.genres)))
        lines.append("  %s" % self.plot)
        lines.append("  Directed by: %s" % ", ".join([str(d) for d in self.directors]))
        lines.append("  Screenplay by: %s" % ", ".join([str(d) for d in self.screenplay_writers]))
        lines.append("  Story by: %s" % ", ".join([str(d) for d in self.story_writers]))
        lines.append("  Novel by: %s" % ", ".join([str(d) for d in self.novel_writers]))
        lines.append("  Writers: %s" % ", ".join([str(d) for d in self.writers]))
        lines.append("  Music by: %s" % ", ".join([str(d) for d in self.music]))
        lines.append("  Executive Producers: %s" % ", ".join([str(d) for d in self.executive_producers]))
        lines.append("  Producers: %s" % ", ".join([str(d) for d in self.producers]))
        lines.append("  Cast: %s" % ", ".join([str(d) for d in self.cast]))
        return "\n".join(lines)
        

class SeriesMetadata(BaseMetadata):
    country = "USA"
    
#'title', 'akas', 'year', 'imdbIndex', 'certificates', 'director', 'writer', 'producer', 'cast', 'writer', 'creator', 'original music', 'plot outline', 'rating', 'votes', 'genres', 'number of seasons', 'number of episodes', 'series years', ]    

class IMDbProxy(PickleSerializerMixin):
    def __init__(self, default_version=1, filename=None):
        PickleSerializerMixin.__init__(self, default_version)
        self.imdb_api = imdb.IMDb(accessSystem='http', adultSearch=1)
        self.create()
        if filename:
            self.loadStateFromFile(filename)
            self.use_cache = True
        else:
            self.use_cache = False
    
    def __str__(self):
        lines = []
        titles = sorted(self.search_cache.keys())
        for title in titles:
            lines.append("%s: %s" % (title, self.search_cache[title]))
        return "\n".join(lines)
    
    def saveStateToFile(self, *args, **kwargs):
        if not self.use_cache:
            print "IMDb Cache not used; not saving."
            return
        PickleSerializerMixin.saveStateToFile(self, *args, **kwargs)
    
    def create(self):
        self.createVersion1()
    
    def createVersion1(self):
        self.search_cache = {}
        self.movie_obj_cache = {}
    
    def packVersion1(self):
        return (self.search_cache, self.movie_obj_cache)
    
    def unpackVersion1(self, data):
        self.search_cache, self.movie_obj_cache = data
        
    def search_movie(self, title):
        if title in self.search_cache:
            print "*** FOUND %s in search cache: " % title
            return self.search_cache[title]
        print "*** NOT FOUND in search cache: %s" % title 
        results = self.imdb_api.search_movie(title)
        print "*** STORING %s in search cache: " % title
        if self.use_cache:
            self.search_cache[title] = results
        return results
        
    def get_movie(self, imdb_id):
        if type(imdb_id) == int:
            imdb_id = "%07d" % imdb_id
        if imdb_id in self.movie_obj_cache:
            print "*** FOUND %s in movie cache: " % imdb_id
            return self.movie_obj_cache[imdb_id]
        print "*** NOT FOUND in movie cache: %s" % imdb_id 
        movie_obj = self.imdb_api.get_movie(imdb_id)
        print "*** STORING %s in movie cache: " % imdb_id
        if self.use_cache:
            self.movie_obj_cache[imdb_id] = movie_obj
        return movie_obj

class MovieMetadataDatabase(MetadataDatabase):
    def __init__(self, default_version=1, imdb_cache=None):
        MetadataDatabase.__init__(self, default_version)
        self.imdb_api = IMDbProxy(filename=imdb_cache)
        self.tmdb_api = tmdb.MovieDb()
    
    def __str__(self):
        lines = []
        lines.append("Movies:")
        for m in sorted(self.movies.values()):
            lines.append(str(m))
        lines.append("People:")
        for p in sorted(self.people.values()):
            lines.append("  %s" % safeprint(p))
        return "\n".join(lines)
    
    def createVersion1(self):
        self.movies = {}
        self.series = {}
        self.people = {}
    
    def packVersion1(self):
        self.imdb_api.saveStateToFile()
        return (self.movies, self.series, self.people)
    
    def unpackVersion1(self, data):
        self.movies = data[0]
        self.series = data[1]
        self.people = data[2]

    def print_entry(self, tfilm):
        #print unicode(dict(tfilm)).encode('ascii', 'replace')
        print "tmdb: imdb_id=%s  name=%s" % (tfilm['imdb_id'], unicode(tfilm['original_name']).encode('ascii', 'replace'))
        print "Posters:"
        biggest = None
        for poster in tfilm['images'].posters:
            for key, value in poster.items():
                if key not in ['id', 'type']:
                    print "  poster: %s" % value
                    biggest = value
    
    def search_movie(self, title):
        if self.imdb_cache:
            results = self.imdb_cache.get_search_results(title)
            if results:
                return results
        results = self.imdb_api.search_movie(title)
        if self.imdb_cache:
            self.imdb_cache.set_search_results(title, results)
        return results

    def guess(self, movie, fetch=False):
        found = []
        try:
            results = self.imdb_api.search_movie(movie.search_title)
        except:
            print "Failed looking up %s" % movie.search_title
            return None
        for result in results:
            imdb_id = result.movieID
            if imdb_id is None:
                continue
            
            if 'movie' in result['kind']:
                if fetch:
                    self.fetch_movie(imdb_id)
            elif 'series' in result['kind']:
                if fetch:
                    self.fetch_series(imdb_id)
            else:
                # It's a video game or something else; skip it
                continue
            
            found.append(result)
        return found
    
    def best_guess(self, movie, fetch=False):
        # First entry in results is assumed to be the best match
        found = self.guess(movie, fetch)
        if found:
            return found[0]
        return None
    
    def fetch_movie(self, imdb_id):
        if imdb_id in self.movies:
            print "Already exists in local movie database"
            return self.movies[imdb_id]
        movie_obj = self.imdb_api.get_movie(imdb_id)
        movie = MovieMetadata(movie_obj, self)
        self.movies[imdb_id] = movie
        return movie
    
    def get_person(self, person_obj):
        id = person_obj.personID
        if id in self.people:
            person = self.people[id]
        else:
            person = Person(person_obj)
            self.people[id] = person
        return person
    
    def prune_people(self, people_obj, match="", max=25):
        """Create list of Person objects where the notes field of the imdb
        Person object matches the criteria.
        
        Side effect: removes matched IMDb Person objects from input list
        """
        persons = []
        unmatched = people_obj[:]
        for p in unmatched:
            if match in p.notes:
                persons.append(self.get_person(p))
                people_obj.remove(p)
                if len(persons) >= max:
                    break
        return persons
        
    def fetch_poster(self, movie, root_dir):
        named_image, _ = os.path.splitext(os.path.basename(movie['pathname']))
        image = os.path.join(root_dir, named_image + ".jpg")
        if os.path.exists(image):
            newname = os.path.join(root_dir, "%s.jpg" % movie.imdb_id)
            print "renaming %s -> %s" % (image, newname)
            os.rename(image, newname)
            return
        return self.fetch_poster_tmdb(movie.imdb_id, root_dir)
    
    def fetch_poster_tmdb(self, imdb_id, root_dir):
        try:
            tfilm = self.db_tmdb[imdb_id]
        except KeyError:
            print "%s not in database!" % imdb_id
            return
        found = None
        for poster in tfilm['images'].posters:
            for key, value in poster.items():
                if key not in ['id', 'type']:
                    print key, value
                    if value.startswith("http"):
                        found = value
                        break
            for key in ['w342', 'mid', 'original']:
                if key in poster:
                    found = poster[key]
                    break
            if found:
                break
        if found:
            filename = found.split("/")[-1]
            (name, extension) = os.path.splitext(filename)
            local_thumb = os.path.join(root_dir, "%s%s" % (imdb_id, extension))
            print local_thumb
            if not os.path.exists(local_thumb) or os.stat(local_thumb)[6] == 0:
                print "Downloading %s poster: %s" % (safeprint(tfilm['name']), found)
                local_file = open(local_thumb, "wb")
                local_file.write(urllib.urlopen(found).read())
                local_file.close()
                print "Downloaded %s poster: %s" % (safeprint(tfilm['name']), local_thumb)
            else:
                print "Found %s poster: %s" % (safeprint(tfilm['name']), local_thumb)
        else:
            print "No poster for %s" % safeprint(tfilm['name'])
