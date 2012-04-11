"""Thread-safe image utilities
"""
import os, sys, time, logging, threading, Queue
from cStringIO import StringIO

import pyglet
import pyglet.image
from PIL import Image, PngImagePlugin

log = logging.getLogger("dinoteeth.image")
log.setLevel(logging.DEBUG)

class ImageAccess(object):
    lock = threading.Lock()
    log = logging.getLogger("slideshow.image")

    @classmethod
    def load(cls, filename, size=None, rotate=False):
        """Force the use of PIL rather than gdk_pixbuf due to a hard-to-
        reproduce segfault in gdkpixbuf.gdk_pixbuf_loader_new()
        """
        image = None
#        with cls.lock:
        if True:
            try:
                img = Image.open(filename)
                if rotate:
                    orientation = 1
                    if hasattr(img, '_getexif'):
                        try:
                            exif = img._getexif()
                            if exif != None and 0x0112 in exif:
                                orientation = exif[0x0112]
                        except:
                            pass
                    if orientation == 6:
                        img = img.transpose(Image.ROTATE_270)
                    elif orientation == 3:
                        img = img.transpose(Image.ROTATE_180)
                    elif orientation == 8:
                        img = img.transpose(Image.ROTATE_90)
                    #img.thumbnail(size, Image.ANTIALIAS)
                    #img.thumbnail(size, Image.BICUBIC)
                    img.thumbnail(size, Image.BILINEAR)
                    #img.thumbnail(size, Image.NEAREST)
                
                img = img.transpose(Image.FLIP_TOP_BOTTOM)

                # Convert bitmap and palette images to component
                if img.mode in ('1', 'P'):
                    img = img.convert()

                if img.mode not in ('L', 'LA', 'RGB', 'RGBA'):
                    raise ImageDecodeException('Unsupported mode "%s"' % img.mode)
                type = GL_UNSIGNED_BYTE
                width, height = img.size

                image = pyglet.image.ImageData(width, height, img.mode, img.tostring())
            except Exception, e:
                cls.log.error("Error loading %s: %s" % (filename, e))
        return image
    
    @classmethod
    def blit(cls, image, x, y):
#        with cls.lock:
#            image.blit(x, y)
        image.blit(x, y)
