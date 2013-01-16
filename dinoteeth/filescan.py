import os, sys, re, bisect, time, glob
from datetime import datetime

from persistent import Persistent

import kaa.metadata

class MediaFile(Persistent):
    media_list = {}
    
    @classmethod
    def guess(cls, media_file, info):
        try:
            baseclass = cls.media_list[info.media]
        except KeyError:
            return None
        return baseclass.guess(media_file, info)

    @classmethod
    def register(cls, kaa_media_type, baseclass):
        cls.media_list[kaa_media_type] = baseclass

    def __init__(self, pathname, flags=""):
        self.pathname = pathname
        self.flags = flags
        self.mtime = -1
        self.scan = None
        self.metadata = None
        self.reset()
    
    def __str__(self):
        return "%s: %s" % (self.pathname, str(self.scan))
    
    def __cmp__(self, other):
        return cmp(self.sort_key(), other.sort_key())
    
    def sort_key(self):
        """Return a key that can be used to sort like-kinds of files,
        e.g.  sorting a list of AVScanBase instances, or sorting GameBase
        instances.  Not designed (yet) to sort among unmatched types.
        
        Different types of MediaFiles may be sortable on the scan or the
        metadata; it depends on the type.  Scan is checked first, then
        metadata.
        """
        if self.scan is not None and hasattr(self.scan, "sort_key"):
            key = self.scan.sort_key()
        elif self.metadata is not None and hasattr(self.metadata, "sort_key"):
            key = self.metadata.sort_key()
        else:
            key = self.pathname
        return key

    def reset(self):
        # Rather than saving a copy of the entire metadata scan, just save the
        # parts that we are going to use later.  This reduces database size by
        # almost an order of magnitude
        info = kaa.metadata.parse(self.pathname)
        
        if os.path.exists(self.pathname):
            self.mtime = os.stat(self.pathname).st_mtime
        else:
            self.mtime = -1
        
#        print info
        if info is None:
            return
        self.scan = self.__class__.guess(self, info)
    
    def is_current(self):
        if os.path.exists(self.pathname):
            print self.pathname, os.stat(self.pathname).st_mtime, self.mtime
            if os.stat(self.pathname).st_mtime == self.mtime:
                return True
        return False
