import os, sys, glob, subprocess

import utils

from model import MenuItem, MenuPopulator


class PhotoDB(object):
    def __init__(self):
        self.paths = []
        self.children = []
    
    def add_path(self, path):
        self.paths.append(path)
    
    def hierarchy(self):
        dirs = []
        for path in self.paths:
            dirs.extend(glob.glob(os.path.join(path, "*")))
        dirs.sort()
        for dir in dirs:
            if os.path.isdir(dir):
                self.children.append(PhotoDir(dir))
        print self.children
        return self


class TopLevelPhoto(MenuPopulator):
    def iter_image_path(self, artwork_loader):
        raise StopIteration
        
    def iter_create(self):
        yield "By Folder", PhotoFolderLookup(self.config)
        yield "Slideshows", SlideshowLookup(self.config)

class PhotoFolderLookup(MenuPopulator):
    def iter_create(self):
        db = self.config.get_photo_database()
        for path in db.paths:
            yield os.path.basename(path), PhotoFolder(self.config, path)

class PhotoFolder(MenuPopulator):
    valid_image_types = ['.jpg', '.png']
    
    def __init__(self, config, path):
        MenuPopulator.__init__(self, config)
        self.path = path
    
    def iter_image_path(self, artwork_loader):
        images = glob.glob(os.path.join(self.path, "*"))
        images.sort()
        for image in images:
            if not os.path.isdir(image):
                _, ext = os.path.splitext(image)
                if ext.lower() in self.valid_image_types:
                    yield image
    
    def iter_create(self):
        dirs = glob.glob(os.path.join(self.path, "*"))
        dirs.sort()
        for path in dirs:
            if os.path.isdir(path):
                yield os.path.basename(path), PhotoFolder(self.config, path)

    def play(self, config=None):
        self.config.prepare_for_external_app()
        print "Starting slideshow for %s" % self.path
        args = [sys.executable, "bin/slideshow.py", "--once", self.path]
        p = subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        output, errors = p.communicate()
        print output
        print errors
        self.config.restore_after_external_app()

    def get_metadata(self):
        return {
            'imagegen': self.thumbnail_mosaic,
            }

class SlideshowLookup(MenuPopulator):
    def iter_create(self):
        db = self.config.get_photo_database()
        for path in db.paths:
            yield path, PhotoFolder(self.config, path)
