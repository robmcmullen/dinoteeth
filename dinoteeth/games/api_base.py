from ..utils import HttpProxyBase

class GameAPI(HttpProxyBase):
    subcategory = None
    
    def __init__(self, settings):
        HttpProxyBase.__init__(self, self.get_cache_dir(settings))
    
    def get_cache_dir(self, settings):
        """Return the cache dir of the subclass
        
        """
        return "/tmp"
    
    @classmethod
    def get_all_subclasses(cls, parent=None, subclassof=None):
        """
        Recursive call to get all classes that have a specified class
        in their ancestry.  The call to __subclasses__ only finds the
        direct, child subclasses of an object, so to find
        grandchildren and objects further down the tree, we have to go
        recursively down each subclasses hierarchy to see if the
        subclasses are of the type we want.

        @param parent: class used to find subclasses
        @type parent: class
        @param subclassof: class used to verify type during recursive calls
        @type subclassof: class
        @returns: list of classes
        """
        if parent is None:
            parent = cls
        if subclassof is None:
            subclassof = cls
        subclasses = set()

        # this call only returns immediate (child) subclasses, not
        # grandchild subclasses where there is an intermediate class
        # between the two.
        classes = parent.__subclasses__()
        for kls in classes:
            # FIXME: this seems to return multiple copies of the same class,
            # but I probably just don't understand enough about how python
            # creates subclasses
            # dprint("%s id=%s" % (kls, id(kls)))
            if issubclass(kls, subclassof) and kls.subcategory is not None:
                subclasses.add(kls)
            # for each subclass, recurse through its subclasses to
            # make sure we're not missing any descendants.
            subs = cls.get_all_subclasses(kls, subclassof)
            if len(subs)>0:
                subclasses.update(subs)
        return list(subclasses)

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
