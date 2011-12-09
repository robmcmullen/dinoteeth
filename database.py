from media import MediaObject, MediaResults


class Database(object):
    def __init__(self, aliases=None):
        if aliases is None:
            aliases = dict()
        self.aliases = aliases
        self.create()
    
    def create(self):
        pass


class DictDatabase(Database):
    def create(self):
        self.cats = {}
    
    def add(self, g):
        guess = MediaObject.convertGuess(g)
        category = guess['type']
        if category is not None:
            if category in self.aliases:
                category = self.aliases[category]
            if category not in self.cats:
                self.cats[category] = {}
            
            self.cats[category][guess['pathname']] = guess
    
    def find(self, category, criteria=None):
        results = MediaResults()
        if category in self.cats:
            cat = self.cats[category]
            if criteria is None:
                criteria = lambda s: True
            for item in cat.itervalues():
                valid = criteria(item)
                if valid:
                    results.append(item)
            results.sort()
        return results
