import os, sys, glob

from media import MovieTitle


class Database(object):
    def __init__(self):
        self.create()
    
    def create(self):
        pass
    
    def scan(self, category, path):
        pass


class DictDatabase(Database):
    def create(self):
        self.cats = {}
    
    def scan(self, category, path):
        if category not in self.cats:
            self.cats[category] = {}
        cat = self.cats[category]
        MovieParser.add_videos_in_path(cat, path)
    
    def find(self, category, criteria=None):
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
    def add_videos_in_path(cls, cat, path):
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
                    cls.add_videos_in_path(cat, video)
            elif os.path.isfile(video):
                print("Checking %s" % video)
                for ext in cls.video_extensions:
                    if video.endswith(ext):
                        valid = True
                        print ("Found valid media: %s" % video)
                        break
                if valid:
                    cls.add_video(cat, video)
    
    @classmethod
    def add_video(cls, cat, filename):
        """Check to see if the filename is associated with a series
        """
        title = MovieTitle(filename)
        cat[title.pathname] = title
