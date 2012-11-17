from ..utils import HttpProxyBase

class GameAPI(HttpProxyBase):
    def __init__(self, settings):
        HttpProxyBase.__init__(self, self.get_cache_dir(settings))
    
    def get_cache_dir(self, settings):
        """Return the cache dir of the subclass
        
        """
        return "/tmp"


class Game(object):
    def __init__(self):
        self.name = ""
        self.id = -1
        self.imdb_id = None
        self.url = ""
        self.default_image_url = ""
        self.all_image_urls = []
        self.publisher = None
        self.publisher_id = None
        self.year = None
        self.year_id = None
        self.genre = None
        self.genre_id = None
        self.country = None
        self.country_id = None
    
    def __unicode__(self):
        return u"%s (%s, %s, %s): %s, %s" % (self.name, self.year, self.publisher, self.country, self.url, self.default_image_url)
    
    def __str__(self):
        return "%s (%s, %s, %s): %s, %s" % (self.name, self.year, self.publisher, self.country, self.url, self.default_image_url)
