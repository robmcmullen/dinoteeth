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
    
    def __str__(self):
        return "%s '%s', id=%s" % (self.__class__.__name__, self.title, self.id)
    
    def __cmp__(self, other):
        return cmp(self.sort_key(), other.sort_key())
    
    def is_fake(self):
        return False
    
    def get_path_prefix(self):
        return os.path.join(self.media_category, self.id)
    
    def get_primary_poster_suffix(self):
        return ""
    
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
        self.metadata_root = settings.metadata_root
    
    def init_proxies(self, settings):
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
    
    def save_poster(self, metadata, url, data, suffix=None):
        """Save posters for the metadata instance

        @param suffix: text (if any) to be appended after the filename but
        before the extension
        """
        path = os.path.join(self.metadata_root, metadata.get_path_prefix())
        dirname = os.path.dirname(path)
        if not os.path.exists(dirname):
            os.makedirs(dirname)
        if suffix is not None:
            path += suffix
        filename, ext = os.path.splitext(url)
        path += ext.lower()
        print "Saving %d bytes from %s to %s" % (len(data), url, path)
        with open(path, "wb") as fh:
            fh.write(data)
    
    def get_poster_filename(self, metadata, suffix=None):
        """Check if poster exists
        
        """
        path = os.path.join(self.metadata_root, metadata.get_path_prefix())
        if suffix is not None:
            path += suffix
        for ext in [".jpg", ".png", ".gif"]:
            filename = path + ext
            if os.path.exists(filename):
                return filename
        return None
    
    def has_poster(self, metadata, suffix=None):
        """Check if poster exists
        
        """
        if suffix is None:
            suffix = metadata.get_primary_poster_suffix()
        path = self.get_poster_filename(metadata, suffix)
        return path is not None
    
