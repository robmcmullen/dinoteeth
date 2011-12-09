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
                if prop in ('title', 'extraTitle', 'series', 'filmSeries'):
                    if metadata[prop]:
                        metadata[prop] = utils.decode_title_text(metadata[prop])
                    else:
                        del metadata[prop]
            if 'season' in metadata:
                metadata['type'] = 'episode'
            else:
                metadata['type'] = 'movie'
            if 'filmSeries' in metadata:
                if 'title' not in metadata:
                    if 'episodeNumber' in metadata and metadata['episodeNumber'] > 1:
                        metadata['title'] = "%s %d" % (metadata['filmSeries'], metadata['episodeNumber'])
                    else:
                        metadata['title'] = metadata['filmSeries']
            guess = Guess(metadata, confidence = 1.0)
            return guess
    return None

class MediaObject(Guess):
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
    
    def __str__(self):
        return self.canonical_title
    
    def pprint(self, level=""):
        print "%s%s: %s" % (level, str(self.__class__.__name__), str(self))
        for child in self.children:
            child.pprint(level + "  ")

    def __cmp__(self, other):
        return cmp(self.decorate(), other.decorate())

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
        entry = (self.get('title', ""),
                 9999,
                 9999,
                 9999,
                 "",
                 )
        return entry
    
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
        # Just a placeholder for now; not sure of the format and how the user
        # is going to select one of the options.
        return [(1, "Stereo"),
                (2, "DTS"),
                (3, "Director's Commentary"),
                ]
    
    def set_audio_options(self, index=-1, **kwargs):
        self.audio = index
        print "FIXME: audio index = %s" % self.audio
    
    def get_subtitle_options(self):
        # Just a placeholder for now; not sure of the format and how the user
        # is going to select one of the options.
        return [(1, "Subtitles [en]"),
                (2, "Closed Captions [en]"),
                (3, "Trivia Track"),
                ]
    
    def set_subtitle_options(self, index=-1, **kwargs):
        self.subtitle = index
        print "FIXME: subtitle index = %s" % self.subtitle
    
    def play(self, config=None):
        client = config.get_media_client()
        last_pos = client.play(self['pathname'], self.audio, self.subtitle)
    
    def resume(self, config=None):
        print "FIXME: Resuming %s" % self


class Movie(Playable, MediaObject):
    def canonicalize(self):
        self.canonical_title = self['title']
        self.in_context_title = self.canonical_title
    
    def decorate(self):
        entry = (self.get('title', ""),
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
        entry = (self.get('title', ""),
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
        text = [str(s) for s in self]
        return "\n".join(text)
    
    def hierarchy(self):
        name_groups = {}
        for guess in self:
            t = guess.group_key
            if t not in name_groups:
                name_groups[t] = []
            name_groups[t].append(guess)
        h = Root("root")
        for guesses in name_groups.itervalues():
            for child in guesses:
                chain = child.decompose()
                h.add_chain(chain)
        #print h.str_hierarchy()
        return h
