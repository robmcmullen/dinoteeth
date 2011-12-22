import os, sys, re, bisect

import utils

from guessit import guess_file_info, Guess


def normalize_guess(guess):
    if guess['type'] == 'movie' and 'title' not in guess:
        title, _ = os.path.splitext(os.path.basename(filename))
        guess['title'] = unicode(title)

def guess_media_info(pathname):
    filename = utils.decode_title_text(pathname)
    guess = guess_file_info(filename, "autodetect", info=['filename'])
    return guess

def guess_custom(pathname, regexps):
    filename, _ = os.path.splitext(pathname)
    for regexp in regexps:
        r = re.compile(regexp)
        match = r.match(filename)
        if match:
            metadata = match.groupdict()
            for prop, value in metadata.items():
                if prop in ('season', 'episodeNumber', 'year', 'extraNumber'):
                    if metadata[prop] is not None:
                        metadata[prop] = int(metadata[prop])
                if prop in ('title', 'extraTitle', 'series', 'franchise'):
                    if metadata[prop]:
                        metadata[prop] = utils.decode_title_text(metadata[prop])
                    else:
                        del metadata[prop]
            if 'season' in metadata:
                metadata['type'] = 'episode'
            else:
                metadata['type'] = 'movie'
            if 'franchise' in metadata:
                if 'title' not in metadata:
                    if 'episodeNumber' in metadata and metadata['episodeNumber'] > 1:
                        metadata['title'] = "%s %d" % (metadata['franchise'], metadata['episodeNumber'])
                    else:
                        metadata['title'] = metadata['franchise']
            guess = Guess(metadata, confidence = 1.0)
            return guess
    return None

class MediaObject(Guess):
    metadata_db = None
    ignore_leading_articles = set()
    
    @classmethod
    def convertGuess(cls, g):
        guess = None
        if g['type'] == 'movie':
            if 'extraNumber' in g:
                guess = MovieBonus(g)
            else:
                guess = Movie(g)
        elif g['type'] == 'episode':
            if 'episodeNumber' in g:
                guess = SeriesEpisode(g)
            elif 'extraNumber' in g:
                guess = SeriesBonus(g)
        if guess is None:
            raise RuntimeError("Unsupported guess type %s" % g['type'])
        return guess
    
    @classmethod
    def setMetadataDatabase(cls, db):
        cls.metadata_db = db
    
    @classmethod
    def setIgnoreLeadingArticles(cls, articles):
        cls.ignore_leading_articles = set(articles)
    
    def __init__(self, other):
        Guess.__init__(self)
        ignore = self.filter_out()
        for k in other:
            if k not in ignore:
                self[k] = other[k]
                if k in other._confidence:
                    self._confidence[k] = other._confidence[k]
                else:
                    self._confidence[k] = -1.0
        self.children = []
        if isinstance(other, MediaObject):
            self.imdb_id = other.imdb_id
            self.metadata = other.metadata
            self.scanned_metadata = other.scanned_metadata
        else:
            self.imdb_id = None
            self.metadata = {}
            self.scanned_metadata = None
        self.set_defaults()
        self.normalize()
    
    def set_defaults(self):
        pass
    
    def filter_out(self):
        return set()
    
    def normalize(self):
        self.add_missing_entries()
        self.calc_group_key()
        self.canonicalize()
        self.calc_sort_key()
    
    def __str__(self):
        return self.canonical_title
    
    def pprint(self, level=""):
        print "%s%s: %s" % (level, str(self.__class__.__name__), str(self))
        for child in self.children:
            child.pprint(level + "  ")

    def __cmp__(self, other):
        return cmp(self.sort_key, other.sort_key)

    def add_missing_entries(self):
        if 'title' not in self:
            title, _ = os.path.splitext(os.path.basename(self['pathname']))
            self['title'] = title
    
    def calc_group_key(self):
        self.group_key = self['type'], self['title']
            
    def canonicalize(self):
        self.in_context_title = self['title']
        self.canonical_title = self['title']

    def decorate(self):
        entry = (self.sort_title,
                 9999,
                 9999,
                 9999,
                 "",
                 )
        return entry
    
    def calc_sort_key(self):
        title = self.canonical_title
        t = title.lower()
        for article in self.ignore_leading_articles:
            a = "%s " % article.lower()
            if t.startswith(a):
                title = title[len(a):] + ", %s" % title[0:len(article)]
                break
        self.sort_title = title
        self.sort_key = self.decorate()
    
    def decompose(self):
        raise RuntimeError

    def add_chain(self, chain):
        if chain:
            node = chain[0]
            pos = bisect.bisect_left(self.children, node)
            if pos != len(self.children) and self.children[pos].group_key == node.group_key:
                #print "Found %s" % node
                pass
            else:
                #print "Inserting %s" % node
                bisect.insort_left(self.children, node)
            parent = self.children[pos]
            parent.add_chain(chain[1:])

    def str_hierarchy(self):
        text = []
        text.append(str(self))
        for node in self.children:
            text.append(node.str_hierarchy())
        return "\n".join(text)
    
    # MenuItem methods
    
    def add_to_menu(self, theme, parent_menu):
        return theme.add_simple_menu(self, parent_menu)
    
    # Metadata scanner for info determined from the file itself
    
    def scan(self, scanner):
        metadata = scanner(self['pathname'])
#        print "Scanned %s" % metadata.filename
#        print metadata.audio
#        print metadata.subtitles
        self.scanned_metadata = metadata
    
    # Textual metadata support routines for info returned from IMDB, etc.
    
    def has_metadata(self, category, value):
        if category in self.metadata:
            c = self.metadata[category]
            if isinstance(c, list):
                return value in c
            else:
                return c == value
        return False


class Root(MediaObject):
    def __init__(self, title):
        other = Guess(title=title, type='root')
        MediaObject.__init__(self, other)


class Playable(object):
    def set_defaults(self):
        self.audio = None
        self.subtitle = None
    
    def is_bonus_feature(self):
        return False
    
    def get_bonus_title(self):
        bonus = "Untitled Bonus Feature"
        if 'extraNumber' in self:
            if 'extraTitle' not in self:
                bonus = "Bonus Feature %s" % str(self['extraNumber'])
            else:
                bonus = "#%s: %s" % (str(self['extraNumber']), str(self['extraTitle']))
        elif 'extraTitle' in self:
            bonus = str(self['extraTitle'])
        return bonus
    
    def get_audio_options(self):
        options = []
        for audio in self.scanned_metadata.iter_audio():
            options.append((audio.id, audio.name))
        if not options:
            # "No audio" is not an option by default; only if there really is
            # no audio available in the media
            options.append((-1, "No audio"))
        return options
    
    def set_audio_options(self, index=-1, **kwargs):
        self.audio = index
        print "FIXME: audio index = %s" % self.audio
    
    def get_subtitle_options(self):
        # Unlike audio, "No subtitles" should always be an option in case
        # people don't want to view subtitles
        options = [(-1, "No subtitles")]
        for subtitle in self.scanned_metadata.iter_subtitles():
            options.append((subtitle.id, subtitle.name))
        return options
    
    def set_subtitle_options(self, index=-1, **kwargs):
        self.subtitle = index
        print "FIXME: subtitle index = %s" % self.subtitle
    
    def get_runtime(self):
        return utils.time_format(self.scanned_metadata.length)
    
    def play(self, config=None):
        win = config.get_main_window()
        if config.options.fullscreen:
            win.set_fullscreen(False)
        client = config.get_media_client()
        last_pos = client.play(self['pathname'], self.audio, self.subtitle)
        if config.options.fullscreen:
            win.set_fullscreen(True)
    
    def resume(self, config=None):
        print "FIXME: Resuming %s" % self


class Movie(Playable, MediaObject):
    def canonicalize(self):
        self.canonical_title = self['title']
        self.in_context_title = self.canonical_title
    
    def decorate(self):
        entry = (self.sort_title,
                 9999,
                 9999,
                 0,
                 "",
                 )
        return entry
    
    def decompose(self):
        return [MovieTitle(self), self]

class MovieBonus(Movie):
    def is_bonus_feature(self):
        return True
    
    def canonicalize(self):
        self.in_context_title = self.get_bonus_title()
        self.canonical_title = "%s %s" % (self['title'], self.in_context_title)
    
    def decorate(self):
        entry = (self.get('title', ""),
                 9999,
                 9999,
                 self.get('extraNumber', 0),
                 self.get('extraTitle', ""),
                 )
        return entry

class MovieTitle(Movie):
    def decorate(self):
        entry = (self.sort_title,
                 9999,
                 9999,
                 9999,
                 "",
                 )
        return entry
    
    def decompose(self):
        return [self]
    
    def add_to_menu(self, theme, parent_menu):
        return theme.add_movie_title_to_menu(self, parent_menu)

class MovieSeries(Movie):
    pass


class SeriesBase(MediaObject):
    def decorate(self):
        entry = (self.get('series', ""),
                 self.get('season', 9999),
                 self.get('episodeNumber', 9999),
                 self.get('extraNumber', 9999),
                 self.get('extraTitle', ""),
                 )
        return entry
    
    def calc_group_key(self):
        self.group_key = self['type'], self['series']
            
    def add_missing_entries(self):
        if 'series' not in self:
            title, _ = os.path.splitext(os.path.basename(self['pathname']))
            self['series'] = title

class SeriesEpisode(Playable, SeriesBase):
    def canonicalize(self):
        self.in_context_title = "Episode %d %s" % (self['episodeNumber'], self.get('episodeTitle',""))
        self.canonical_title = "%s Season %d %s" % (self['series'], self['season'], self.in_context_title)
    
    def decompose(self):
        return [Series(self), Season(self), self]
    
    def add_to_menu(self, theme, parent_menu):
        return theme.add_movie_options_to_menu(self, parent_menu)

class SeriesBonus(SeriesEpisode):
    def is_bonus_feature(self):
        return True
    
    def canonicalize(self):
        self.in_context_title = self.get_bonus_title()
        self.canonical_title = "%s Season %d %s" % (self['series'], self['season'], self.in_context_title)
    
    def decompose(self):
        return [Series(self), Season(self), self]

class Series(SeriesBase):
    def filter_out(self):
        return set(['pathname', 'season', 'episodeNumber', 'title', 'extraNumber', 'extraTitle'])
    
    def decorate(self):
        entry = (self.get('series', ""),
                 9999,
                 9999,
                 9999,
                 "",
                 )
        return entry
    
    def canonicalize(self):
        self.canonical_title = self['series']
        self.in_context_title = self.canonical_title
    
    def decompose(self):
        return [self]

class Season(SeriesBase):
    def filter_out(self):
        return set(['pathname', 'episodeNumber', 'title', 'extraNumber', 'extraTitle'])
    
    def decorate(self):
        entry = (self.get('series', ""),
                 self.get('season', 9999),
                 9999,
                 9999,
                 "",
                 )
        return entry
    
    def canonicalize(self):
        self.in_context_title = "Season %d" % self['season']
        self.canonical_title = "%s %s" % (self['series'], self.in_context_title)
    
    def decompose(self):
        return [Series(self), self]


class MediaResults(list):
    def __str__(self):
        text = ["%d: %s" % (i, str(s)) for i,s in enumerate(self)]
        return "\n".join(text)
    
    def hierarchy(self):
        name_groups = self.get_name_groups()
        h = Root("root")
        for guesses in name_groups.itervalues():
            for child in guesses:
                chain = child.decompose()
                h.add_chain(chain)
        #print h.str_hierarchy()
        return h
    
    def get_name_groups(self):
        """Return a dict keyed on [media].group_key containing a list
        of all media with that group key
        """
        if not hasattr(self, '_name_groups'):
            name_groups = {}
            for guess in self:
                t = guess.group_key
                if t not in name_groups:
                    name_groups[t] = []
                name_groups[t].append(guess)
            self._name_groups = name_groups
        return self._name_groups
    
    def all_metadata(self, category):
        """Return a set containing the union of all metadata of the specific
        category
        
        """
        union = set()
        for media in self:
            if category in media.metadata:
                values = media.metadata[category]
                if isinstance(values, list):
                    union.update(values)
                else:
                    union.add(values)
        return union
    
    def subset_by_metadata(self, category, value):
        name_groups = self.get_name_groups()
        subset = MediaResults()
        found_groups = set()
        for media in self:
            if media.has_metadata(category, value) and media.group_key not in found_groups:
                found_groups.add(media.group_key)
                subset.extend(name_groups[media.group_key])
        return subset

    def thumbnail_mosaic(self, artwork_loader, thumbnail_factory, x, y, w, h):
        import pyglet
        
        min_x = x
        max_x = x + w
        min_y = y
        y = y + h
        nominal_x = 100
        nominal_y = 140
        for media in self:
            id = media.metadata['imdb_id']
            imgpath = artwork_loader.get_poster_filename(id)
            if imgpath is not None:
                thumb_image = thumbnail_factory.get_image(imgpath)
                if x + nominal_x > max_x:
                    x = min_x
                    y -= nominal_y
                if y < min_y:
                    break
                thumb_image.blit(x + (nominal_x - thumb_image.width) / 2, y - nominal_y + (nominal_y - thumb_image.height) / 2, 0)
                x += nominal_x


class AudioTrack(object):
    def __init__(self, id, lang="en", codec="unknown", name=None):
        self.id = id
        if name is None:
            name = "Audio Track %d" % id
        self.name = name
        self.lang = lang
        self.codec = codec

class SubtitleTrack(object):
    def __init__(self, id, lang="en", format="unknown", name=None):
        self.id = id
        if name is None:
            name = "Subtitle %d" % id
        self.name = name
        self.lang = lang
        self.format = format
