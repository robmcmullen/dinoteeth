import os, sys


class MetadataLoader(object):
    def __init__(self, proxies):
        self.proxies = proxies
    
    def search(self, title_key):
        """Return list of possible metadata IDs given the title key
        
        If possible, list should be ordered from most to least likely based on
        an appropriate criteria.
        """
        return []


class Register(object):
    category_map = {}
    
    @classmethod
    def get_class(cls, category):
        try:
            baseclass = Register.category_map[category]
        except KeyError:
            raise RuntimeError("Metadata category %s not known" % category)
        return baseclass

def register(category, baseclass):
    Register.category_map[category] = baseclass

def get_loader(media_file_or_title_key, proxies):
    if hasattr(media_file_or_title_key, "category"):
        category = media_file_or_title_key.category
    elif hasattr(media_file_or_title_key, "scan") and media_file_or_title_key.scan is not None:
        category = media_file_or_title_key.scan.title_key.category
    baseclass = Register.get_class(category)
    return baseclass(proxies)
