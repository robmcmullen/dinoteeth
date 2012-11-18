import os, sys

from persistent import Persistent

import settings



class BaseMetadata(Persistent):
    media_category = None

    def __init__(self, id, title_key):
        if type(id) == int:
            self.id = "tt%07d" % id
        elif isinstance(id, basestring) and not id.startswith("tt"):
            self.id = "tt%s" % id
        else:
            self.id = id
        if title_key is None:
            self.title = ""
            self.year = None
            self.subcategory = None
        else:
            self.title = title_key.title
            self.year = title_key.year
            self.kind = title_key.subcategory
        self.date_added = -1
        self.starred = False
    
    def __cmp__(self, other):
        return cmp(self.sort_key(), other.sort_key())
    
    def is_fake(self):
        return False
    
    def get_path_prefix(self):
        return os.path.join(self.media_category, self.id)
    
    def sort_key(self, credit=None):
        t = self.title.lower()
        return (t, self.year)


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
    
    def fetch_posters(self, metadata):
        """Load posters for the metadata instance

        """
        pass
    
    def save_poster(self, metadata, url, data, season=None):
        """Save posters for the metadata instance

        """
        metadata_root = "/tmp"
        path = os.path.join(metadata_root, metadata.get_path_prefix())
        dirname = os.path.dirname(path)
        if not os.path.exists(dirname):
            os.makedirs(dirname)
        if season is not None:
            path += "-s%02d" % season
        filename, ext = os.path.splitext(url)
        path += ext
        print "Saving %d bytes from %s to %s" % (len(data), url, path)
        with open(path, "wb") as fh:
            fh.write(data)
        
