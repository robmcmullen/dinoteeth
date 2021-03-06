#!/usr/bin/env python
"""
Get TMDB/IMDB metadata for movies in the database
"""

import os, re, time, collections, logging
from ..third_party.sentence import first_sentence

from persistent import Persistent

from .. import utils
from .. import settings
from ..metadata import BaseMetadata

log = logging.getLogger("dinoteeth.home_theater")
log.setLevel(logging.DEBUG)


def safestr(s):
    if isinstance(s, basestring):
        return unicode(s).encode('utf-8')
    return s


class Company(Persistent):
    zodb_mapping_name = "companies"
    imdb_prefix = "co"
    
    def __init__(self, company_obj, id=None, name=None):
        if company_obj:
            self.id = company_obj.companyID
            self.name = company_obj['name']
        else:
            self.id = id
            self.name = name
    
    def __cmp__(self, other):
        return cmp(self.name, other.name)
    
    def __str__(self):
        return safestr(self.name)
    
    def __unicode__(self):
        return u"%s" % self.name

class Person(Persistent):
    zodb_mapping_name = "people"
    imdb_prefix = "nm"
    
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

class FilmSeries(Persistent):
    zodb_mapping_name = "film_series"
    imdb_prefix = "--"
    
    def __init__(self, tmdb_obj, id=None, name=None):
        if tmdb_obj:
            self.id = tmdb_obj['id']
            self.name = tmdb_obj['name']
            if self.name.endswith(" Collection"):
                self.name = self.name[:-11]
        else:
            self.id = id
            self.name = name
    
    def __cmp__(self, other):
        return cmp(self.name, other.name)
    
    def __str__(self):
        return safestr(self.name)
    
    def __unicode__(self):
        return u"%s" % self.name


class HomeTheaterMetadata(BaseMetadata):
    imdb_country = None
    imdb_language = None
    iso_3166_1 = None
    ignore_leading_articles = ["a", "an", "the"]
    media_category = "video"
    media_subcategory = None

    def __init__(self, id, title_key):
        BaseMetadata.__init__(self, id, title_key)
        self.title_index = ""
        self.runtimes = []
    
    def sort_key(self, credit=None):
        if credit and hasattr(self, credit):
            if credit == "film_series":
                sort_key = (self.film_series.name, self.film_number)
                return sort_key
#            else:
#                sort_key = getattr(self, credit)
#            return sort_key
        t = self.title.lower()
        for article in self.ignore_leading_articles:
            a = "%s " % article.lower()
            if t.startswith(a):
                t = t[len(a):] + ", %s" % t[0:len(article)]
                break
        return (t, self.year, self.title_index)
    
    def get_tmdb_country_list(self, tmdb_obj, block_key, key, country, if_empty="", coerce=None):
        found = None
        print block_key
        if block_key in tmdb_obj:
            subobj = tmdb_obj[block_key]
            for block in subobj:
                if block['iso_3166_1'] == country:
                    found = block[key]
                    break
        elif key in tmdb_obj:
            found = tmdb_obj[key]
        if found is not None:
            if coerce:
                try:
                    found = coerce(found)
                except:
                    log.error("Can't coerce %s to %s for %s in get_tmdb_country_list" % (found, str(coerce), block))
                    found = if_empty
            return found
        return if_empty
        
    def get_imdb_country_list(self, imdb_obj, key, country, skip=None, if_empty="", coerce=None):
        if not imdb_obj.has_key(key): # Note: key in imdb_obj fails; must use has_key
            return if_empty
        default = if_empty
        values = imdb_obj[key]
#        print "get_imdb_country_list[%s]: %s" % (key, str(values))
        for value in values:
            if ":" in value:
                c, v = value.split(":", 1)
                if c == country:
                    if skip and skip in v:
                        continue
                    if "::" in v:
                        v, _ = v.split("::", 1)
                    if coerce:
                        try:
                            v = coerce(v)
                        except:
                            log.error("Can't coerce %s to %s for %s in get_imdb_country_list" % (v, str(coerce), imdb_obj))
                            v = if_empty
                    return v
            else:
                default = value
        if default:
            try:
                if coerce:
                    default = coerce(default)
                return default
            except:
                log.error("Can't coerce %s to %s for %s in get_imdb_country_list" % (v, str(coerce), imdb_obj))
        return if_empty
    
    def get_imdb_list(self, imdb_obj, key, skip=None, coerce=None):
        if not imdb_obj.has_key(key): # Note: key in imdb_obj fails; must use has_key
            return []
        ret_list = []
        values = imdb_obj[key]
        for value in values:
            if "::" in value:
                value, _ = value.split("::", 1)
            if ":" in value:
                c, v = value.split(":", 1)
            else:
                v = value
            if coerce:
                try:
                    v = coerce(v)
                except:
                    log.error("Can't coerce %s to %s for %s in get_imdb_list" % (v, str(coerce), imdb_obj))
                    continue
            ret_list.append(v)
        return ret_list
    
    def get_obj(self, imdb_obj, key):
        if not imdb_obj.has_key(key):
            return []
        obj = imdb_obj[key]
#        print "get_obj[%s]: %s" % (key, str(obj))
        return list(obj)
    
    # IMDb contains a lot of alternate titles; this list is used to prune down
    # the acceptable possible titles by excluding any AKAs with these tags.
    # See e.g.  http://www.imdb.com/title/tt0017136/releaseinfo#akas
    skip_title_parts = ["promotional title", "poster title", "IMAX", "DVD title", "complete title", "original title", "short title", "restored version"]
    skip_title_re = re.compile("|".join(skip_title_parts))
    
    # Remove any year parens in the title; this will be added when displayed
    end_year_re = re.compile("(.+) +(\([12][0-9]{3}\))")
    
    def get_title(self, imdb_obj, country, language, tmdb_obj=None, tvdb_obj=None):
        best = None
        if tmdb_obj:
            best = tmdb_obj['title']
        elif tvdb_obj:
            best = tvdb_obj.data['seriesname']
        if best:
            match = self.end_year_re.match(best)
            if match:
                best = match.group(1)
            return best
        if imdb_obj.has_key('akas'):
            possibilities = []
            for aka in imdb_obj['akas']:
                if "::" in aka:
                    title, note = aka.split("::")
                    parts = note.split(",")
                    for part in parts:
                        if self.skip_title_re.search(part):
                            continue
                        if country in part or "imdb display title" in part or ("International" in part and language in part):
                            possibilities.append((title, part))
            
            def try_possibility(cname, lang):
                for title, part in possibilities:
                    if cname in part:
                        if lang is None:
                            return title
                        elif lang in part:
                            return title
                
            best = try_possibility(country, language)
            if not best:
                best = try_possibility("International", language)
            if not best:
                best = try_possibility(country, None)
        if not best:
            best = imdb_obj['title']
        return best
    
    def prune_people(self, imdb_obj, match="", max=25):
        """Create list of Person objects where the notes field of the imdb
        Person object matches the criteria.
        
        Side effect: removes matched IMDb Person objects from input list
        """
        persons = []
        unmatched = imdb_obj[:]
        for p in unmatched:
            if match in p.notes:
                persons.append(Person(p))
                imdb_obj.remove(p)
                if len(persons) >= max:
                    break
        return persons
    
    def prune_companies(self, imdb_obj, max=5):
        """Create list of Company objects where the notes field of the imdb
        Person object matches the criteria.
        
        Side effect: removes matched IMDb Person objects from input list
        """
        companies = []
        unmatched = imdb_obj[:]
        for p in unmatched:
            companies.append(Company(p))
            imdb_obj.remove(p)
            if len(companies) >= max:
                break
        return companies
    
    def merge_database_objects(self, db):
        """Loop through all persistent objects to point to any that are already
        in the database
        
        Persistent objects may be in any list in the instance.
        """
        if self.id is None:
            self.id = "fake%d" % db.zodb.get_unique_id()
        for name in dir(self):
            attr = getattr(self, name)
            if isinstance(attr, list):
                try:
                    obj = attr[0]
                except IndexError:
                    continue
                if hasattr(obj, "zodb_mapping_name"):
                    self.merge_mapping(db, name, attr)
        db.metadata[self.id] = self
    
    def merge_mapping(self, db, name, attr):
        mapping = db.zodb.get_mapping(attr[0].zodb_mapping_name)
        newitems = []
        for item in attr:
            if item.id not in mapping:
                log.debug("  adding %s %s (%s)" % (item.zodb_mapping_name, item.id, str(item)))
                mapping[item.id] = item
            else:
                log.debug("  found %s %s (%s)" % (item.zodb_mapping_name, item.id, str(item)))
            newitems.append(mapping[item.id])
        setattr(self, name, newitems)
    
    def lambdaify(self, criteria):
        if isinstance(criteria, collections.Callable):
            return criteria
        if isinstance(criteria, collections.Iterable) and not isinstance(criteria, basestring):
            return lambda a: a in criteria
        if criteria is not None:
            return lambda a: a == criteria
        return lambda a: True

    def match(self, credit, criteria=None, convert=None):
        if credit is None:
            return True
        log.debug("match: credit=%s criteria=%s" % (credit, criteria))
        criteria = self.lambdaify(criteria)
        if convert is None:
            convert = lambda d: d
        if hasattr(self, credit):
            item = getattr(self, credit)
            if item is None:
                return False
            if isinstance(item, basestring):
                log.debug("match: %s credit=%s, item=%s %s converted=%s result=%s" % (self.title, credit, item, type(item), convert(item), criteria(convert(item))))
                return criteria(convert(item))
            elif isinstance(item, collections.Iterable):
                log.debug("match: %s credit=%s, ITERABLE:" % (self.title, credit))
                for i in item:
                    log.debug("  match: item=%s %s converted=%s result=%s" % (i, type(i), convert(i), criteria(convert(i))))
                    if criteria(convert(i)):
                        return True
            else:
                log.debug("match: %s credit=%s, item=%s %s converted=%s result=%s" % (self.title, credit, item, type(item), convert(item), criteria(convert(item))))
                return criteria(convert(item))
        return False
    
    def iter_items_of(self, credit):
        if hasattr(self, credit):
            item = getattr(self, credit)
            log.debug("iter_items_of: credit=%s, item=%s %s" % (credit, item, type(item)))
            if isinstance(item, basestring):
                yield item
            elif isinstance(item, collections.Iterable):
                for i in item:
                    yield i
            else:
                yield item
    
    def get_runtime(self):
        if len(self.runtimes):
            return self.runtimes[0]
        return 0
    runtime = property(get_runtime)
    
    def is_tv(self):
        return self.kind in ['series', 'tv movie', 'tv series', 'tv mini series']
    
    def is_mini_series(self):
        return self.kind in ['tv mini series']
    
    def expected_episodes(self, season=1):
        if not hasattr(self, 'seasons'):
            return 1
        if season not in self.seasons:
            return -1
        return len(self.seasons[season])
    
    def update_with_media_files(self, media_files):
        for item in media_files:
            if item.mtime > self.date_added:
                self.date_added = item.mtime

        pass
    
    def get_audio_markup(self, media_file):
        audio = ""
        for id, selected, name in media_file.scan.get_audio_options():
            if selected:
                audio += "<b>%s</b>\n" % name
            else:
                audio += "%s\n" % name
        subtitle = ""
        for id, selected, name in media_file.scan.get_subtitle_options(media_file.pathname):
            if selected:
                subtitle += "<b>%s</b>\n" % name
            else:
                subtitle += "%s\n" % name

        text = u"""

<u>Available Audio Tracks:</u>
%s

<u>Available Subtitle Tracks:</u>
%s""" % (_(audio), _(subtitle))
        return text

    def get_last_played_markup(self, media_file):
        date, position = media_file.scan.get_last_played_stats()
        text = u""
        if date is not None:
            if position is not None:
                text += """

<b>Paused:</b> %s
<b>Paused At:</b> %s\n""" % (_(date), _(position))
            else:
                text += """\n

<b>Last Played:</b> %s
                \n""" % _(date)
        return text

    def get_file_info_markup(self, media_file):
        text = """\n
%s\n""" % _(media_file.pathname)
        return text
    
    def get_icon_codes(self, media_file):
        codes = []
        try:
            print "cert: %s" % self.certificate
            codes = ["ratings/%s" % self.certificate]
        except AttributeError:
            pass
        if media_file:
            try:
                codes.append("video/%s" % media_file.scan.video[0]['codec'])
            except:
                pass
        return codes


class FakeMetadata(HomeTheaterMetadata):
    imdb_prefix = "tt"

    def __init__(self, id, title_key, scans):
        HomeTheaterMetadata.__init__(self, id, title_key)
    
    def is_fake(self):
        return True

class FakeMovieMetadata(FakeMetadata):
    media_subcategory = "movie"
    
    def get_markup(self, media_file=None):
        title = self.title
        if self.year:
            title += u" (%s)" % self.year
        text = u"<b>%s</b>\n" % _(title)
        if media_file:
            text += self.get_audio_markup(media_file)
            text += self.get_last_played_markup(media_file)
            text += self.get_file_info_markup(media_file)
        else:
            text += u"\nMetadata not found in IMDb or TMDB"
        return text

class FakeSeriesMetadata(FakeMetadata):
    media_subcategory = "series"
    
    def get_markup(self, media_file=None):
        title = self.title
        if self.year:
            title += u" (%s)" % self.year
        text = u"<b>%s</b>\n" % _(title)
        
        if media_file:
            text += "\n<b>Episode:</b> %s" % (_(media_file.scan.episode))
            text += self.get_audio_markup(media_file)
            text += self.get_last_played_markup(media_file)
            text += self.get_file_info_markup(media_file)
        else:
            text += u"\nMetadata not found in IMDb or TMDB"
        return text


class MovieMetadata(HomeTheaterMetadata):
    media_subcategory = "movie"
    imdb_prefix = "tt"
    
    def __init__(self, movie_obj, tmdb_obj):
        title_key = utils.TitleKey("video", movie_obj['kind'], self.get_title(movie_obj, settings.imdb_country, settings.imdb_language, tmdb_obj=tmdb_obj), movie_obj['year'])
        HomeTheaterMetadata.__init__(self, movie_obj.imdb_id, title_key)
        self.title_index = movie_obj.get('imdbIndex', "")
        if tmdb_obj:
            cert = self.get_tmdb_country_list(tmdb_obj, 'releases', 'certification', settings.iso_3166_1, if_empty="")
        else:
            cert = None
        if not cert:
            cert = self.get_imdb_country_list(movie_obj, 'certificates', settings.imdb_country, skip="TV rating", if_empty="unrated")
        self.certificate = cert
        self.plot = movie_obj.get('plot outline', "")
        self.genres = movie_obj.get('genres', list())
        self.rating = movie_obj.get('rating', "")
        self.votes = movie_obj.get('votes', "")
        self.runtimes = self.get_imdb_list(movie_obj, 'runtimes', coerce=int)
        if tmdb_obj:
            released = self.get_tmdb_country_list(tmdb_obj, 'releases', 'release_date', settings.iso_3166_1, if_empty="")
        else:
            released = None
        if not released:
            released = unicode(self.year)
        self.release_date = released
        
        directors = self.get_obj(movie_obj, 'director')
        self.directors = self.prune_people(directors)
        
        producers = self.get_obj(movie_obj, 'producer')
        self.executive_producers = self.prune_people(producers, 'executive producer')
        self.producers = self.prune_people(producers)
        
        writers = self.get_obj(movie_obj, 'writer')
        self.novel_writers = self.prune_people(writers, 'novel')
        self.screenplay_writers = self.prune_people(writers, 'screenplay')
        self.story_writers = self.prune_people(writers, 'story')
        self.writers = self.prune_people(writers)
        
        music = self.get_obj(movie_obj, 'original music')
        self.music = self.prune_people(music)
        
        cast = self.get_obj(movie_obj, 'cast')
        self.cast = self.prune_people(cast)
        
        companies = self.get_obj(movie_obj, 'production companies')
        self.companies = self.prune_companies(companies)
        
        if tmdb_obj and tmdb_obj['belongs_to_collection']:
            film_series = FilmSeries(tmdb_obj['belongs_to_collection'])
        else:
            film_series = None
        self.film_series = film_series
        self.film_number = 1
        self.date_added = -1
    
    def update_with_media_files(self, media_files):
        HomeTheaterMetadata.update_with_media_files(self, media_files)
        item = media_files.get_main_feature()
        if item is None:
            return
        log.debug((u"update_with_media_files: %s: %s" % (self.title, item)).encode('utf8'))
        try:
            self.film_number = item.scan.film_number
        except:
            pass
    
    def get_markup(self, media_file=None):
        genres = u", ".join([unicode(i) for i in self.genres])
        directors = u", ".join([unicode(i) for i in self.directors])
        producers = u", ".join([unicode(i) for i in self.producers[0:3]])
        writers = u", ".join([unicode(i) for i in self.writers])
        actors = u", ".join([unicode(i) for i in self.cast])
        music = u", ".join([unicode(i) for i in self.music])
        title = self.title
        if self.year:
            title += u" (%s)" % self.year
        text = u"""<b>%s</b>

%s

<b>Rated:</b> %s
<b>Released:</b> %s
<b>Genre:</b> %s
<b>IMDb ID:</b> %s
""" % (_(title), _(self.plot), _(self.certificate),
                          _(self.release_date), _(genres), self.id)
        if media_file:
            text += self.get_audio_markup(media_file)
            text += self.get_last_played_markup(media_file)
            text += self.get_file_info_markup(media_file)
        else:
            text += u"""
<b>Directed by:</b> %s
<b>Produced by:</b> %s
<b>Written by:</b> %s
<b>Music by:</b> %s
<b>Actors:</b> %s
<b>Runtime:</b> %s
<b>Rating:</b> %s/10""" % (_(directors), _(producers), _(writers), _(music),
                           _(actors), _(self.runtime), _(self.rating))
        return text


class SeriesMetadata(HomeTheaterMetadata):
    media_subcategory = "series"
    imdb_prefix = "tt"
    
    def __init__(self, movie_obj, tvdb_obj):
#'title', 'akas', 'year', 'imdbIndex', 'certificates', 'director', 'writer', 'producer', 'cast', 'writer', 'creator', 'original music', 'plot outline', 'rating', 'votes', 'genres', 'number of seasons', 'number of episodes', 'series years', ]
#['akas', u'art department', 'art direction', 'aspect ratio', 'assistant director', 'camera and electrical department', 'canonical title', 'cast', 'casting director', 'certificates', 'cinematographer', 'color info', u'costume department', 'costume designer', 'countries', 'cover url', 'director', u'distributors', 'editor', u'editorial department', 'full-size cover url', 'genres', 'kind', 'languages', 'long imdb canonical title', 'long imdb title', 'make up', 'miscellaneous companies', 'miscellaneous crew', u'music department', 'number of seasons', 'plot', 'plot outline', 'producer', u'production companies', 'production design', 'production manager', 'rating', 'runtimes', 'series years', 'smart canonical title', 'smart long imdb canonical title', 'sound crew', 'sound mix', 'title', 'votes', 'writer', 'year']
        title_key = utils.TitleKey("video", movie_obj['kind'], self.get_title(movie_obj, settings.imdb_country, settings.imdb_language, tvdb_obj=tvdb_obj), movie_obj['year'])
        HomeTheaterMetadata.__init__(self, movie_obj.imdb_id, title_key)
        self.title_index = movie_obj.get('imdbIndex', "")
        self.certificate = self.get_imdb_country_list(movie_obj, 'certificates', settings.imdb_country, if_empty="unrated")
        self.plot = movie_obj.get('plot outline', "")
        self.genres = movie_obj.get('genres', list())
        self.rating = movie_obj.get('rating', "")
        self.votes = movie_obj.get('votes', "")
        self.num_seasons = movie_obj.get('number of seasons', 1)
        self.series_years = movie_obj.get('series years', "")
        self.runtimes = self.get_imdb_list(movie_obj, 'runtimes', coerce=int)
        
        directors = self.get_obj(movie_obj, 'director')
        self.directors = self.prune_people(directors)
        
        producers = self.get_obj(movie_obj, 'producer')
        self.executive_producers = self.prune_people(producers, 'executive producer')
        
        writers = self.get_obj(movie_obj, 'writer')
        self.writers = self.prune_people(writers)
        
        music = self.get_obj(movie_obj, 'original music')
        self.music = self.prune_people(music)
        
        cast = self.get_obj(movie_obj, 'cast')
        self.cast = self.prune_people(cast)
        
        companies = self.get_obj(movie_obj, 'production companies')
        self.companies = self.prune_companies(companies)
        
        if tvdb_obj and tvdb_obj.data['network']:
            network = Company(None, None, tvdb_obj.data['network'])
        else:
            distributors = self.get_obj(movie_obj, 'distributors')
            networks = self.prune_companies(distributors, 1)
            if networks:
                network = networks[0]
            else:
                network = None
        self.network = network
        self.date_added = -1
        
        self.parse_tvdb_obj(tvdb_obj)
    
    def parse_tvdb_obj(self, show):
        self.seasons = dict()
        if not show:
            return
        seasons = len(show) - 1
        print "%s on %s, nominal runtime: %s" % (show.data['seriesname'], show.data['network'], show.data['runtime'])
#        print "Total seasons (not including specials): %d" % seasons
        for season in range(1,seasons+1):
            if season not in show:
                continue
            episodes = len(show[season])
#            print "  Season #%d: %d episodes" % (season, episodes)
            episode_keys = show[season].keys()
            s = dict()
            for episode in episode_keys:
                e = show[season][episode]
#                print (u"    Episode #%s (abs=%s dvd=%s): %s" % (e['episodenumber'], e['absolute_number'], e['dvd_episodenumber'], e['episodename'])).encode('utf8')
                epnum = episode
                for key in ['dvd_episodenumber', 'episodenumber']:
                    val = e.get(key, -1)
                    if val is not None:
                        num = int(float(val))
                        if num >=0:
                            epnum = num
                            break
                overview = e['overview']
                if overview:
                    plot = first_sentence(overview)
                else:
                    plot = ""
                if e['gueststars']:
                    guest = [a.strip() for a in e['gueststars'].split("|") if a]
                    guest = guest[0:5]
                else:
                    guest = []
                ep = {'title': e['episodename'],
                      'guest': guest,
                      'plot': plot,
                      'aired': e['firstaired'],
                      }
                s[epnum] = ep
            self.seasons[season] = s

    def get_markup(self, media_file=None):
        genres = u", ".join([unicode(i) for i in self.genres])
        directors = u", ".join([unicode(i) for i in self.directors])
        producers = u", ".join([unicode(i) for i in self.executive_producers])
        writers = u", ".join([unicode(i) for i in self.writers])
        actors = u", ".join([unicode(i) for i in self.cast])
        music = u", ".join([unicode(i) for i in self.music])
        title = _(self.title)
        if self.year:
            title += u" (%s)" % self.year
        text = u"""<b>%s</b>
""" % title
        
        if media_file:
            try:
                s = self.seasons[media_file.scan.season]
                #print s
                e = s[media_file.scan.episode]
                #print e
                text += """
<b>Episode:</b> %s
<b>Aired:</b> %s

<b><i>%s</i></b>

%s

<b>Guest Stars:</b> %s
""" % (_(media_file.scan.episode), _(e['aired']), _(e['title']), _(e['plot']), _(", ".join(e['guest'])))
            except KeyError:
                pass
            text += self.get_audio_markup(media_file)
            text += self.get_last_played_markup(media_file)
            text += self.get_file_info_markup(media_file)
        else:
            text += """
%s

<b>Network:</b> %s %s""" % (_(self.plot), _(self.network), _(self.series_years))
            if not self.is_mini_series():
                text += """
<b>Number of Seasons:</b> %s""" % self.num_seasons
            text += """
<b>Rated:</b> %s
<b>Genre:</b> %s
<b>IMDb ID:</b> %s
""" % (self.certificate, genres, self.id)
            text += u"""
<b>Produced by:</b> %s
<b>Directed by:</b> %s
<b>Written by:</b> %s
<b>Music by:</b> %s
<b>Actors:</b> %s
<b>Rating:</b> %s/10""" % (_(producers), _(directors), _(writers), _(music), _(actors), _(self.rating))
            
        return text
