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
    def __init__(self, other):
        Guess.__init__(self)
        dict.update(self, other)
        for prop in other:
            if prop in other._confidence:
                self._confidence[prop] = other._confidence[prop]
            else:
                self._confidence[prop] = -1.0

    def __cmp__(self, other):
        return cmp(self.decorate(), other.decorate())

    def decorate(self):
        if self['type'] == 'movie':
            entry = (self.get('title', ""),
                     9999,
                     self.get('extraNumber', 9999),
                     self.get('extraTitle', ""),
                     )
        elif self['type'] == 'episode':
            entry = (self.get('series', ""),
                     self.get('episodeNumber', 9999),
                     self.get('extraNumber', 9999),
                     self.get('extraTitle', ""),
                     )
        else:
            entry = (self.get('title', ""),
                     9999,
                     9999,
                     "",
                     )
        return entry
    

class DictDatabase(Database):
    def create(self):
        self.cats = {}
    
    def add(self, g):
        guess = SortableGuess(g)
        category = guess['type']
        if category is not None:
            if category in self.aliases:
                category = self.aliases[category]
            if category not in self.cats:
                self.cats[category] = {}
            
            self.cats[category][guess['pathname']] = guess
            print "added: %s" % guess.nice_string()
    
    def find(self, category, criteria=None):
        if category not in self.cats:
            return []
        cat = self.cats[category]
        results = []
        if criteria is None:
            criteria = lambda s: True
        for item in cat.itervalues():
            valid = criteria(item)
            if valid:
                results.append(item)
        #results = self.sort(results)
        results.sort()
        return results
