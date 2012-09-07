#!/usr/bin/env python
"""
Get TMDB/IMDB metadata for movies in the database
"""

import os, time, collections, logging
from third_party.sentence import first_sentence

from persistent import Persistent

log = logging.getLogger("dinoteeth.metadata")
log.setLevel(logging.DEBUG)


def safestr(s):
    if isinstance(s, basestring):
        return unicode(s).encode('utf-8')
    return s


class Company(Persistent):
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


class BaseMetadata(Persistent):
    imdb_country = None
    iso_3166_1 = None
    ignore_leading_articles = ["a", "an", "the"]
    media_category = None
    credit_map = [
        # Title, attribute, limit_category (one of: 'series', 'movies' or None), converter (to change the data; e.g. change a raw timestamp into a month/year for bucketing), reverse sort flag (True or False/None)
        ("By Date Added", "date_added", None, lambda d: time.strftime("%B %Y", time.localtime(d)), True),
        ("By Genre", "genres", None, None, False),
        ("By Film Series", "film_series", "movies", None, False),
        ("By Director", "directors", None, None, False),
        ("By Actor", "cast", None, None, False),
        ("By Executive Producer", "executive_producers", "series", None, False),
        ("By Producer", "producers", "movies", None, False),
        ("By Production Company", "companies", None, None, False),
        ("By Composer", "music", None, None, False),
        ("By Screenwriter", "screenplay_writers", "movies", None, False),
        ("Based on a Novel By", "novel_writers", "movies", None, False),
        ("By Year", "year", None, None, False),
        ("By Years Broadcast", "series_years", "series", None, False),
        ("By Broadcast Network", "network", "series", None, False),
        ("By Number of Seasons", "num_seasons", "series", None, False),
        ("By Rating", "certificate", None, None, False),
        ]
    
    def __cmp__(self, other):
        return cmp(self.sort_key(), other.sort_key())
    
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
    
    def get_title(self, imdb_obj, country):
        best = imdb_obj['title']
        if imdb_obj.has_key('akas'):
            for aka in imdb_obj['akas']:
                if "::" in aka:
                    title, note = aka.split("::")
                    if "imdb display title" in note:
                        # Only allow official display titles
#                        print safestr(title)
                        for part in note.split(","):
#                            print "  %s" % part
                            if country in part:
                                best = title
        return best
    
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
    
    def update_with_media_scans(self, media_scans):
        for scan in media_scans:
            if scan.mtime > self.date_added:
                self.date_added = scan.mtime

        pass
    
    def get_audio_markup(self, media_scan):
        audio = ""
        for id, selected, name in media_scan.get_audio_options():
            if selected:
                audio += "<b>%s</b>\n" % name
            else:
                audio += "%s\n" % name
        subtitle = ""
        for id, selected, name in media_scan.get_subtitle_options():
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

    def get_last_played_markup(self, media_scan):
        date, position = media_scan.get_last_played_stats()
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
        text += """\n
%s\n""" % _(media_scan.pathname)
        return text


class FakeMetadata(BaseMetadata):
    imdb_prefix = "tt"

    def __init__(self, id, title_key, scans, db):
        self.id = id
        self.kind = title_key[2]
        self.title = title_key[0]
        self.year = title_key[1]
        self.title_index = ""
        self.date_added = -1
    
    def __unicode__(self):
        lines = []
        lines.append(u"%s %s (%s)" % (self.id, self.title, self.year))

class FakeMovieMetadata(FakeMetadata):
    media_category = "movies"
        
    def get_markup(self, media_scan=None):
        title = self.title
        if self.year:
            title += u" (%s)" % self.year
        text = u"<b>%s</b>\n" % _(title)
        if media_scan:
            text += self.get_audio_markup(media_scan)
            text += self.get_last_played_markup(media_scan)
        else:
            text += u"\nMetadata not found in IMDb or TMDB"
        return text

class FakeSeriesMetadata(FakeMetadata):
    media_category = "series"
        
    def get_markup(self, media_scan=None):
        title = self.title
        if self.year:
            title += u" (%s)" % self.year
        text = u"<b>%s</b>\n" % _(title)
        
        if media_scan:
            text += "\n<b>Episode:</b> %s" % (_(media_scan.episode))
            text += self.get_audio_markup(media_scan)
            text += self.get_last_played_markup(media_scan)
        else:
            text += u"\nMetadata not found in IMDb or TMDB"
        return text


class MovieMetadata(BaseMetadata):
    media_category = "movies"
    imdb_prefix = "tt"
    
    def __init__(self, movie_obj, tmdb_obj, db):
        self.id = movie_obj.imdb_id
        self.kind = movie_obj['kind']
        self.title = self.get_title(movie_obj, self.imdb_country)
        self.year = movie_obj['year']
        self.title_index = movie_obj.get('imdbIndex', "")
        if tmdb_obj:
            cert = self.get_tmdb_country_list(tmdb_obj, 'releases', 'certification', self.iso_3166_1, if_empty="")
        else:
            cert = None
        if not cert:
            cert = self.get_imdb_country_list(movie_obj, 'certificates', self.imdb_country, skip="TV rating", if_empty="unrated")
        self.certificate = cert
        self.plot = movie_obj.get('plot outline', "")
        self.genres = movie_obj.get('genres', list())
        self.rating = movie_obj.get('rating', "")
        self.votes = movie_obj.get('votes', "")
        self.runtimes = self.get_imdb_list(movie_obj, 'runtimes', coerce=int)
        if tmdb_obj:
            released = self.get_tmdb_country_list(tmdb_obj, 'releases', 'release_date', self.iso_3166_1, if_empty="")
        else:
            released = None
        if not released:
            released = unicode(self.year)
        self.release_date = released
        
        directors = self.get_obj(movie_obj, 'director')
        self.directors = db.prune_people(directors)
        
        producers = self.get_obj(movie_obj, 'producer')
        self.executive_producers = db.prune_people(producers, 'executive producer')
        self.producers = db.prune_people(producers)
        
        writers = self.get_obj(movie_obj, 'writer')
        self.novel_writers = db.prune_people(writers, 'novel')
        self.screenplay_writers = db.prune_people(writers, 'screenplay')
        self.story_writers = db.prune_people(writers, 'story')
        self.writers = db.prune_people(writers)
        
        music = self.get_obj(movie_obj, 'original music')
        self.music = db.prune_people(music)
        
        cast = self.get_obj(movie_obj, 'cast')
        self.cast = db.prune_people(cast)
        
        companies = self.get_obj(movie_obj, 'production companies')
        self.companies = db.prune_companies(companies)
        
        if tmdb_obj and tmdb_obj['belongs_to_collection']:
            film_series = db.get_film_series(tmdb_obj['belongs_to_collection'])
        else:
            film_series = None
        self.film_series = film_series
        self.film_number = 1
        self.date_added = -1
    
    def update_with_media_scans(self, media_scans):
        BaseMetadata.update_with_media_scans(self, media_scans)
        scan = media_scans.get_main_feature()
        if scan is None:
            return
        log.debug((u"update_with_media_scans: %s: %s" % (self.title, scan)).encode('utf8'))
        self.film_number = scan.film_number
    
    def __unicode__(self):
        lines = []
        lines.append(u"%s %s (%s) %s" % (self.id, self.title, self.year, self.title_index))
        if not self.certificate:
            cert = "unrated"
        else:
            cert = self.certificate
        lines.append(u"  %s %smin rating=%s, %s votes" % (cert, self.runtime, self.rating, self.votes))
        lines.append(u"  %s" % (", ".join(self.genres)))
        lines.append(u"  %s" % self.plot)
        lines.append(u"  Directed by: %s" % ", ".join([unicode(d) for d in self.directors]))
        lines.append(u"  Screenplay by: %s" % ", ".join([unicode(d) for d in self.screenplay_writers]))
        lines.append(u"  Story by: %s" % ", ".join([unicode(d) for d in self.story_writers]))
        lines.append(u"  Novel by: %s" % ", ".join([unicode(d) for d in self.novel_writers]))
        lines.append(u"  Writers: %s" % ", ".join([unicode(d) for d in self.writers]))
        lines.append(u"  Music by: %s" % ", ".join([unicode(d) for d in self.music]))
        lines.append(u"  Executive Producers: %s" % ", ".join([unicode(d) for d in self.executive_producers]))
        lines.append(u"  Producers: %s" % ", ".join([unicode(d) for d in self.producers]))
        lines.append(u"  Cast: %s" % ", ".join([unicode(d) for d in self.cast]))
        return "\n".join(lines)

    def get_markup(self, media_scan=None):
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
""" % (_(title), _(self.plot), _(self.certificate),
                          _(self.release_date), _(genres))
        if media_scan:
            text += self.get_audio_markup(media_scan)
            text += self.get_last_played_markup(media_scan)
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


class SeriesMetadata(BaseMetadata):
    media_category = "series"
    imdb_prefix = "tt"
    
    def __init__(self, movie_obj, tvdb_obj, db):
#'title', 'akas', 'year', 'imdbIndex', 'certificates', 'director', 'writer', 'producer', 'cast', 'writer', 'creator', 'original music', 'plot outline', 'rating', 'votes', 'genres', 'number of seasons', 'number of episodes', 'series years', ]
#['akas', u'art department', 'art direction', 'aspect ratio', 'assistant director', 'camera and electrical department', 'canonical title', 'cast', 'casting director', 'certificates', 'cinematographer', 'color info', u'costume department', 'costume designer', 'countries', 'cover url', 'director', u'distributors', 'editor', u'editorial department', 'full-size cover url', 'genres', 'kind', 'languages', 'long imdb canonical title', 'long imdb title', 'make up', 'miscellaneous companies', 'miscellaneous crew', u'music department', 'number of seasons', 'plot', 'plot outline', 'producer', u'production companies', 'production design', 'production manager', 'rating', 'runtimes', 'series years', 'smart canonical title', 'smart long imdb canonical title', 'sound crew', 'sound mix', 'title', 'votes', 'writer', 'year']
        self.id = movie_obj.imdb_id
        self.kind = movie_obj['kind']
        self.title = self.get_title(movie_obj, self.imdb_country)
        self.year = movie_obj['year']
        self.title_index = movie_obj.get('imdbIndex', "")
        self.certificate = self.get_imdb_country_list(movie_obj, 'certificates', self.imdb_country, if_empty="unrated")
        self.plot = movie_obj.get('plot outline', "")
        self.genres = movie_obj.get('genres', list())
        self.rating = movie_obj.get('rating', "")
        self.votes = movie_obj.get('votes', "")
        self.num_seasons = movie_obj.get('number of seasons', 1)
        self.series_years = movie_obj.get('series years', "")
        self.runtimes = self.get_imdb_list(movie_obj, 'runtimes', coerce=int)
        
        directors = self.get_obj(movie_obj, 'director')
        self.directors = db.prune_people(directors)
        
        producers = self.get_obj(movie_obj, 'producer')
        self.executive_producers = db.prune_people(producers, 'executive producer')
        
        writers = self.get_obj(movie_obj, 'writer')
        self.writers = db.prune_people(writers)
        
        music = self.get_obj(movie_obj, 'original music')
        self.music = db.prune_people(music)
        
        cast = self.get_obj(movie_obj, 'cast')
        self.cast = db.prune_people(cast)
        
        companies = self.get_obj(movie_obj, 'production companies')
        self.companies = db.prune_companies(companies)
        
        if tvdb_obj and tvdb_obj.data['network']:
            network = db.get_company_by_name(tvdb_obj.data['network'])
        else:
            distributors = self.get_obj(movie_obj, 'distributors')
            networks = db.prune_companies(distributors, 1)
            if networks:
                network = networks[0]
            else:
                network = None
        self.network = network
        self.date_added = -1
        
        self.parse_tvdb_obj(tvdb_obj)
    
    def __unicode__(self):
        lines = []
        lines.append(u"%s %s (%s) %s" % (self.id, self.title, self.series_years, self.title_index))
        if not self.certificate:
            cert = "unrated"
        else:
            cert = self.certificate
        lines.append(u"  %s %s rating=%s, %s votes" % (cert, self.network, self.rating, self.votes))
        lines.append(u"  %s" % (", ".join(self.genres)))
        lines.append(u"  %s" % self.plot)
        lines.append(u"  Executive Producers: %s" % ", ".join([unicode(d) for d in self.executive_producers]))
        lines.append(u"  Directed by: %s" % ", ".join([unicode(d) for d in self.directors]))
        lines.append(u"  Writers: %s" % ", ".join([unicode(d) for d in self.writers]))
        lines.append(u"  Music by: %s" % ", ".join([unicode(d) for d in self.music]))
        lines.append(u"  Cast: %s" % ", ".join([unicode(d) for d in self.cast]))
        lines.append(u"  Production Companies: %s" % ", ".join([unicode(d) for d in self.companies]))
        return "\n".join(lines)
    
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

    def get_markup(self, media_scan=None):
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
        
        if media_scan:
            try:
                s = self.seasons[media_scan.season]
                #print s
                e = s[media_scan.episode]
                #print e
                text += """
<b>Episode:</b> %s
<b>Aired:</b> %s

<b><i>%s</i></b>

%s

<b>Guest Stars:</b> %s
""" % (_(media_scan.episode), _(e['aired']), _(e['title']), _(e['plot']), _(", ".join(e['guest'])))
            except KeyError:
                pass
            text += self.get_audio_markup(media_scan)
            text += self.get_last_played_markup(media_scan)
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
""" % (self.certificate, genres)
            text += u"""
<b>Produced by:</b> %s
<b>Directed by:</b> %s
<b>Written by:</b> %s
<b>Music by:</b> %s
<b>Actors:</b> %s
<b>Rating:</b> %s/10""" % (_(producers), _(directors), _(writers), _(music), _(actors), _(self.rating))
            
        return text
