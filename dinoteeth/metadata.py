import os, sys

import settings

class MetadataLoader(object):
    category_map = {}
    
    @classmethod
    def get_class(cls, title_key):
        try:
            subcat_map = cls.category_map[title_key.category]
        except KeyError:
            raise RuntimeError("Metadata category %s not known" % title_key.category)
        subcat = title_key.subcategory
        if subcat not in subcat_map:
            subcat = "*"
        try:
            baseclass = subcat_map[subcat]
        except KeyError:
            raise RuntimeError("Metadata category %s/%s not known" % (title_key.category, title_key.subcategory))
        return baseclass

    @classmethod
    def register(cls, category, subcategory, baseclass):
        if category not in cls.category_map:
            cls.category_map[category] = {}
        if subcategory is None:
            subcategory = "*"
        cls.category_map[category][subcategory] = baseclass

    @classmethod
    def get_loader(cls, media_file_or_title_key):
        if hasattr(media_file_or_title_key, "scan") and media_file_or_title_key.scan is not None:
            title_key = media_file_or_title_key.scan.title_key
        else:
            title_key = media_file_or_title_key
        baseclass = cls.get_class(title_key)
        return baseclass()

    def __init__(self):
        self.init_proxies(settings)
    
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
