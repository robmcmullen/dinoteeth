"""Thread-safe image utilities
"""
import os, sys, time, urllib, logging, threading, Queue
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
                width, height = img.size

                image = (width, height, img.mode, img.tostring())
                print repr(image[3][0:200])
                image = pyglet.image.ImageData(*image)
            except Exception, e:
                cls.log.error("Error loading %s: %s" % (filename, e))
        return image
    
    @classmethod
    def pyglet_from_image(cls, filename, image):
        if image is None:
            raise RuntimeError("Bad image: %s" % filename)
        image = pyglet.image.ImageData(*image)
        return image
    
    @classmethod
    def blit(cls, image, x, y):
        with cls.lock:
            image.blit(x, y)

class ArtworkLoader(object):
    def __init__(self, base_dir, default_poster, poster_dir="posters", cache_size=100):
        self.base_dir = base_dir
        self.poster_dir = os.path.join(self.base_dir, poster_dir)
        self.use_cache = False
        self.cache = {}
        self.default_poster_path = default_poster
        self.default_poster = None
        self.check_dirs()
    
    def clone(self):
        clone = self.__class__(self.base_dir, self.default_poster_path)
        clone.poster_dir = self.poster_dir
        clone.default_poster = None
        return clone
    
    def check_dirs(self):
        if not os.path.exists(self.base_dir):
            os.mkdir(self.base_dir)
        if not os.path.exists(self.poster_dir):
            os.mkdir(self.poster_dir)
    
    def get_default_poster(self):
        import pyglet
        if self.default_poster is None:
            self.default_poster = pyglet.image.load(self.default_poster_path)
        return self.default_poster
    
    def get_poster_basename(self, imdb_id, season=None, ext=".jpg"):
        if season is not None:
            basename = "%s-%s%s" % (imdb_id, season, ext)
        else:
            basename = "%s%s" % (imdb_id, ext)
        return basename
    
    def construct_filename(self, imdb_id, season=None):
        basename = self.get_poster_basename(imdb_id, season)
        filename = os.path.join(self.poster_dir, basename)
        return filename
    
    def get_poster_filename(self, imdb_id, season=None):
        if imdb_id in self.cache:
            return self.cache[imdb_id][0]
        elif imdb_id is not None:
            filename = self.construct_filename(imdb_id, season)
            if os.path.exists(filename):
                return filename
        return None
    
    def has_poster(self, imdb_id, season=None):
        return self.get_poster_filename(imdb_id, season) is not None
    
    def save_poster_from_url(self, imdb_id, url, season=None):
        filename = url.split("/")[-1]
        (name, extension) = os.path.splitext(filename)
        pathname = self.construct_filename(imdb_id, season)
        log.debug(pathname)
        if not os.path.exists(pathname) or os.path.getsize(pathname) == 0:
            log.debug("Downloading %s poster: %s" % (imdb_id, url))
            bytes = urllib.urlopen(url).read()
            if extension.lower() != ".jpg":
                #FIXME: convert to jpg
                pass
            fh = open(pathname, "wb")
            fh.write(bytes)
            fh.close()
            log.debug("Downloaded %s poster as %s" % (imdb_id, pathname))
            downloaded = True
        else:
            log.debug("Found %s poster: %s" % (imdb_id, pathname))
            downloaded = False
        return downloaded
    
    def get_poster(self, imdb_id, season=None):
        key = (imdb_id, season)
        if key in self.cache:
            return self.cache[key][1]
        elif imdb_id is not None:
            filename = self.get_poster_filename(imdb_id, season)
            if filename is not None:
                poster = ImageAccess.load(filename)
                if self.use_cache:
                    self.cache[key] = (filename, poster)
                return poster
        return self.get_default_poster()
    
    def get_image(self, imagepath):
        if imagepath in self.cache:
            return self.cache[imagepath][1]
        filename = os.path.join(self.base_dir, imagepath)
        if os.path.exists(filename):
            image = ImageAccess.load(filename)
            if self.use_cache:
                self.cache[imagepath] = (filename, image)
            return image
        return self.get_default_poster()

class ScaledArtworkLoader(ArtworkLoader):
    def __init__(self, full_size_loader, poster_width):
        self.full_size_loader = full_size_loader
        self.poster_width = poster_width
        poster_dir = "posters-scaled-width-%d" % poster_width
        ArtworkLoader.__init__(self, self.full_size_loader.base_dir, self.full_size_loader.default_poster_path, poster_dir)
    
    def clone(self):
        full_size_clone = self.full_size_loader.clone()
        clone = self.__class__(full_size_clone, self.poster_width)
        return clone
    
    def save_poster_from_url(self, imdb_id, url, season=None):
        downloaded = self.full_size_loader.save_poster_from_url(imdb_id, url, season)
        self.scale_poster(imdb_id, url, season, force=downloaded)
    
    def scale_poster(self, imdb_id, url, season=None, force=False):
        full_image = self.full_size_loader.get_poster_filename(imdb_id, season)
        if full_image:
            scaled_pathname = self.construct_filename(imdb_id, season)
            print "Full size: %s\nScaled: %s" % (full_image, scaled_pathname)
            if force:
                pass
            elif os.path.exists(scaled_pathname) and os.path.getsize(scaled_pathname) > 0 and os.path.getmtime(scaled_pathname) >= os.path.getmtime(full_image):
                log.debug("Found %s scaled poster: %s" % (imdb_id, scaled_pathname))
                return
            img = Image.open(full_image)
            height = img.size[1] * img.size[0] / self.poster_width
            size = (self.poster_width, height)
            img.thumbnail(size, Image.ANTIALIAS)
            img.save(scaled_pathname, "JPEG", quality=90)
            log.debug("Created %s scaled poster: %s" % (imdb_id, scaled_pathname))
