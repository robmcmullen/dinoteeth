import os, sys

from persistent import Persistent
from PIL import Image

import settings
from updates import UpdateManager

import logging
log = logging.getLogger("dinoteeth.metadata")


class BaseMetadata(Persistent):
    media_category = None
    media_subcategory = None

    def __init__(self, id, title_key):
        if type(id) == int:
            self.id = "tt%07d" % id
        elif isinstance(id, basestring) and not id.startswith("tt"):
            self.id = "tt%s" % id
        else:
            self.id = id
        self.set_title_key(title_key)
        self.date_added = -1
        self.starred = False
    
    def set_title_key(self, title_key):
        if title_key is None:
            self.title = ""
            self.year = None
            self.subcategory = None
        else:
            self.title = title_key.title
            self.year = title_key.year
            self.kind = title_key.subcategory
    
    def __str__(self):
        return "%s '%s', id=%s" % (self.__class__.__name__, self.title, self.id)
    
    def __unicode__(self):
        return u"%s '%s', id=%s" % (self.__class__.__name__, self.title, self.id)
    
    def __cmp__(self, other):
        return cmp(self.sort_key(), other.sort_key())
    
    def is_fake(self):
        return False
    
    def get_path_prefix(self):
        if self.id is None:
            raise RuntimeError("Can't get path prefix of metadata with no id: %s" % (str(self)))
        # convert to utf-8 because metadata ID may be unicode
        return os.path.join(self.media_category, self.media_subcategory, self.id).encode('utf-8')
    
    def sort_key(self, credit=None):
        t = self.title.lower()
        return (t, self.year)


class MetadataLoader(object):
    category_map = {}
    
    @classmethod
    def get_class(cls, cat, subcat):
        try:
            subcat_map = cls.category_map[cat]
        except KeyError:
            raise RuntimeError("Metadata category %s not known" % cat)
        if subcat not in subcat_map:
            subcat = "*"
        try:
            baseclass = subcat_map[subcat]
        except KeyError:
            raise RuntimeError("Metadata category %s/%s not known" % (cat, subcat))
        return baseclass

    @classmethod
    def register(cls, cat, subcat, baseclass):
        if cat not in cls.category_map:
            cls.category_map[cat] = {}
        if subcat is None:
            subcat = "*"
        cls.category_map[cat][subcat] = baseclass

    @classmethod
    def get_loader(cls, obj):
        if hasattr(obj, "scan") and obj.scan is not None:
            cat = obj.scan.title_key.category
            subcat = obj.scan.title_key.subcategory
        elif hasattr(obj, "media_category") and obj.media_category is not None:
            cat = obj.media_category
            subcat = obj.media_subcategory
        else:
            cat = obj.category
            subcat = obj.subcategory
        baseclass = cls.get_class(cat, subcat)
        return baseclass()
    
    @classmethod
    def get_user_specified_metadata_id(cls, title_key):
        try:
            mid = settings.user_title_key_map[title_key]
        except KeyError:
            return
        log.info("Found user metadata id %s for %s" % (mid, title_key))
        return mid

    @classmethod
    def get_metadata(cls, title_key, scans):
        loader = MetadataLoader.get_loader(title_key)
        metadata = None
        mid = loader.get_user_specified_metadata_id(title_key)
        if mid:
            metadata = loader.get_metadata_by_id(mid)
        if not metadata:
            metadata = loader.best_guess(title_key, scans)
        return metadata

    def __init__(self):
        self.init_proxies(settings)
        self.metadata_root = settings.metadata_root
        self.poster_width = settings.poster_width
    
    def init_proxies(self, settings):
        pass
    
    def search(self, title_key):
        """Return list of possible metadata IDs given the title key
        
        If possible, list should be ordered from most to least likely based on
        an appropriate criteria.
        """
        return []
    
    def get_basic_metadata(self, search_result):
        """Return a basic metadata instance from a search result
        """
        raise NotImplementedError()
    
    def get_metadata_by_id(self, imdb_id):
        """Return a metadata instance given a known valid id
        """
        raise NotImplementedError()
    
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
        path = self.get_poster_filename_from_url(metadata, url, suffix)
        log.debug("Saving %d bytes from %s to %s" % (len(data), url, path))
        with open(path, "wb") as fh:
            fh.write(data)
        self.scale_poster(path)
    
    def get_poster_filename_from_url(self, metadata, url, suffix=None):
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
        return path

    def get_poster_filename(self, metadata, suffix=None):
        """Check if poster exists
        
        """
        if metadata.id is None:
            return None
        path = os.path.join(self.metadata_root, metadata.get_path_prefix())
        if suffix is not None:
            path += suffix
        for ext in [".jpg", ".png", ".gif"]:
            filename = path + ext
            if os.path.exists(filename):
                return filename
        return None
    
    def get_poster_suffix(self, **kwargs):
        """Loader-specific suffix generator.
        
        Given a keyword (e.g.  "season"), return a suffix that will identify
        the image associated with that keyword.
        """
        return ""
    
    def get_poster(self, metadata, **kwargs):
        """Check if poster exists
        
        """
        suffix = self.get_poster_suffix(**kwargs)
        path = self.get_poster_filename(metadata, suffix)
        log.debug("get_poster: %s" % path)
        return path
    
    def get_poster_background(self, metadata):
        task = self.get_poster_background_task(metadata)
        log.debug("starting task %s" % task)
        UpdateManager.start_task(task)
    
    def get_poster_background_task(self, metadata):
        return None
    
    def has_poster(self, metadata, **kwargs):
        """Check if poster exists
        
        """
        path = self.get_poster(metadata, **kwargs)
        return path is not None
    
    def scale_poster(self, filename):
        img = Image.open(filename)
        if img.size[0] <= self.poster_width:
            return
        height = img.size[1] * img.size[0] / self.poster_width
        size = (self.poster_width, height)
        img.thumbnail(size, Image.ANTIALIAS)
        img.save(filename, "JPEG", quality=90)
        log.debug("Created scaled poster: %s" % (filename))
    
    def get_known_posters(self, metadata, **kwargs):
        """Get all the known posters for the given metadata
        
        Return a list of tuples, where each tuple is a url and a path that will
        be used to cache that url
        """
        return []

    def get_icon(self, icon_code):
        path = os.path.join(self.metadata_root, "icons", icon_code).encode('utf-8')
        for ext in [".jpg", ".png", ".gif"]:
            if os.path.exists(path + ext):
                return path + ext
        return None
