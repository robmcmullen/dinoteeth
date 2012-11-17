import os, sys


class MetadataLoader(object):
    category_map = {}
    
    @classmethod
    def get_class(cls, category):
        try:
            baseclass = cls.category_map[category]
        except KeyError:
            raise RuntimeError("Metadata category %s not known" % category)
        return baseclass

    @classmethod
    def register(cls, category, baseclass):
        cls.category_map[category] = baseclass

    @classmethod
    def get_loader(cls, media_file_or_title_key):
        if hasattr(media_file_or_title_key, "category"):
            category = media_file_or_title_key.category
        elif hasattr(media_file_or_title_key, "scan") and media_file_or_title_key.scan is not None:
            category = media_file_or_title_key.scan.title_key.category
        baseclass = cls.get_class(category)
        return baseclass()

    def __init__(self):
        self.init_proxies()
    
    def init_proxies(self):
        pass
    
    def search(self, title_key):
        """Return list of possible metadata IDs given the title key
        
        If possible, list should be ordered from most to least likely based on
        an appropriate criteria.
        """
        return []
    
    def best_guess(self, title_key, scans):
        """Return best guess for metadata given the list of MediaFiles that
        match the specified title key.
        """
        return []
