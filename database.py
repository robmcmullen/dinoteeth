import bisect

from guessit.guess import Guess

class Database(object):
    def __init__(self, aliases=None):
        if aliases is None:
            aliases = dict()
        self.aliases = aliases
        self.create()
    
    def create(self):
        pass


class SortableGuess(Guess):
    @classmethod
    def convertGuess(cls, g):
        guess = None
        if g['type'] == 'movie':
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
        
        self.normalize()
    
    def filter_out(self):
        return set()
    
    def normalize(self):
        self.add_missing_entries()
        self.calc_group_key()
        self.canonicalize()
    
    def __str__(self):
        return self.canonical_title

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
            if pos != len(self.children) and self.children[pos].canonical_title == node.canonical_title:
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
    
    def get_items(self):
        return [self.in_context_title]

class Root(SortableGuess):
    def __init__(self, title):
        other = Guess(title=title, type='root')
        SortableGuess.__init__(self, other)

class Movie(SortableGuess):
    def add_missing_entries(self):
        if 'title' not in self:
            title, _ = os.path.splitext(os.path.basename(self['pathname']))
            self['title'] = title
    
    def decorate(self):
        entry = (self.get('title', ""),
                 9999,
                 9999,
                 self.get('extraNumber', 0),
                 self.get('extraTitle', ""),
                 )
        return entry
    
    def decompose(self):
        return [MovieTitle(self), self]
    
    def is_bonus_feature(self):
        return 'extraNumber' in self or 'extraTitle' in self
    
    def get_bonus_title(self):
        bonus = []
        if 'extraNumber' in self:
            bonus.append(str(self['extraNumber']))
        if 'extraTitle' in self:
            bonus.append(str(self['extraTitle']))
        return " ".join(bonus)
    
    def get_items(self, previous):
        if self.is_bonus_feature():
            bonus = self.get_bonus_title()
            if previous and previous.is_bonus_feature():
                return ["  " + bonus]
            else:
                return ["Bonus Features", "  " + bonus]
        return [self.in_context_title, "  Play", "  Resume", "Audio Options", "  Stereo", "  DTS", "  Commentary 1", "Subtitles", "  Closed Captions", "  Subtitles", "  Trivia Track"]

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

class MovieSeries(Movie):
    pass

class SeriesEpisode(SortableGuess):
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
            
    def canonicalize(self):
        self.in_context_title = "Episode %d %s" % (self['episodeNumber'], self.get('episodeTitle',""))
        self.canonical_title = "%s Season %d %s" % (self['series'], self['season'], self.in_context_title)
    
    def decompose(self):
        return [Series(self), Season(self), self]

class SeriesBonus(SeriesEpisode):
    def canonicalize(self):
        self.in_context_title = "Bonus Feature %d %s" % (self['extraNumber'], self.get('extraTitle',""))
        self.canonical_title = "%s Season %d %s" % (self['series'], self['season'], self.in_context_title)
    
    def decompose(self):
        return [Series(self), Season(self), self]

class Series(SeriesEpisode):
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

class Season(SeriesEpisode):
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


class GuessResults(list):
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


class DictDatabase(Database):
    def create(self):
        self.cats = {}
    
    def add(self, g):
        guess = SortableGuess.convertGuess(g)
        category = guess['type']
        if category is not None:
            if category in self.aliases:
                category = self.aliases[category]
            if category not in self.cats:
                self.cats[category] = {}
            
            self.cats[category][guess['pathname']] = guess
    
    def find(self, category, criteria=None):
        if category not in self.cats:
            return []
        cat = self.cats[category]
        results = GuessResults()
        if criteria is None:
            criteria = lambda s: True
        for item in cat.itervalues():
            valid = criteria(item)
            if valid:
                results.append(item)
        results.sort()
        return results
