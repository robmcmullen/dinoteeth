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
    
    def add(self, guess):
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
            criteria = lambda s: s
        for item in cat.itervalues():
            result = criteria(item)
            if result:
                results.append(result)
        results.sort()
        return results
