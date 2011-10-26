import os, sys, glob

import pyglet

class MplayerTarget(object):
    def __init__(self, config, pathname):
        self.config = config
        self.fullpath = pathname
        self.dirname, self.filename = os.path.split(pathname)
        self.fileroot, self.fileext = os.path.splitext(self.filename)
        self.title = self.config.decode_title_text(self.fileroot)
        self.details = "Details for %s" % self.title
        self.image = None
    
    def __cmp__(self, other):
        return cmp(self.title, other.title)
    
    def get_image(self):
        if self.image is None:
            imagedir = os.path.join(self.dirname, ".thumbs")
            for ext in [".jpg", ".png"]:
                imagepath = os.path.join(imagedir, self.fileroot + ext)
                print "checking %s" % imagepath
                if os.path.exists(imagepath):
                    self.image = pyglet.image.load(imagepath)
                    print "loaded %s" % imagepath
                    break
            if self.image is None:
                self.image = self.config.get_default_poster()
        return self.image
