import os, sys, glob

from media import guess_media_info

class Database(object):
    def __init__(self, aliases=None):
        if aliases is None:
            aliases = dict()
        self.aliases = aliases
        self.create()
    
    def create(self):
        pass
    
    def scan(self, category, path):
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
    
    def scan(self, category, path):
        for video in MovieParser.scan_path(path):
            guess = guess_media_info(video)
            self.add(guess)
    
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

class MovieParser(object):
    video_extensions = ['.vob', '.mp4', '.avi', '.wmv', '.mov', '.mpg', '.mpeg', '.mpeg4', '.mkv', '.flv']
    exclude = []
    verbose = True
    
    @classmethod
    def scan_path(cls, path):
        videos = glob.glob(os.path.join(path, "*"))
        for video in videos:
            valid = False
            if os.path.isdir(video):
                if not video.endswith(".old"):
                    if self.exclude:
                        match = cls.exclude.search(video)
                        if match:
                            if cls.verbose: print("Skipping dir %s" % video)
                            continue
                    print("Checking dir %s" % video)
                    yield video
            elif os.path.isfile(video):
                print("Checking %s" % video)
                for ext in cls.video_extensions:
                    if video.endswith(ext):
                        valid = True
                        print ("Found valid media: %s" % video)
                        break
                if valid:
                    yield video
