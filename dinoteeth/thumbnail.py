"""Common cache for thumbnails described at:

http://people.freedesktop.org/~vuntz/thumbnail-spec-cache/

This imprementation is reworked from http://sourceforge.net/projects/comix/ to
support PIL rather than GTK for image creation.

Original GPL source: http://comix.svn.sourceforge.net/viewvc/comix/trunk/src/thumbnail.py?revision=321&view=markup
"""

import os, tempfile, mimetypes
from urllib import pathname2url, url2pathname
from hashlib import md5

from PIL import Image, PngImagePlugin


def get_home_dir():
    return os.path.expanduser("~")

def get_home_subdir(relpath):
    return os.path.join(get_home_dir(), relpath)

def get_default_thumbnail_dir():
    return get_home_subdir(".thumbnails/normal")

class ImageTooSmallException(RuntimeError):
    pass

class AbstractThumbnailFactory(object):
    def __init__(self, basedir=None, size=128):
        if not basedir:
            basedir = get_default_thumbnail_dir()
        self.basedir = basedir
        if not os.path.isdir(self.basedir):
            os.makedirs(self.basedir, 0700)
        if size <= 128:
            size = 128
        else:
            size = 256
        self.size = (size, size)
    
    def get_thumbnail_file(self, imgpath, create=False):
        """Return a thumbnail path for the file at <path> by looking in the
        directory of stored thumbnails.  If no thumbnail for <path> can be
        produced (for whatever reason), return None.
        """
        thumbpath = self._path_to_thumbpath(imgpath)
        if not os.path.exists(thumbpath):
            if create:
                return self.create_thumbnail(imgpath)
            return None
        try:
            info = Image.open(thumbpath).info
            try:
                mtime = int(info['Thumb::MTime'])
            except Exception:
                mtime = -1
            if int(os.stat(imgpath).st_mtime) != mtime:
                return self.create_thumbnail(imgpath)
            return thumbpath
        except Exception:
            #return None
            raise

    def delete_thumbnail(self, imgpath):
        """Delete the thumbnail (if it exists) for the file at <path>.
        
        If <dst_dir> is set it is the base thumbnail directory, if not we use
        the default .thumbnails/normal/.
        """
        thumbpath = self._path_to_thumbpath(imgpath)
        if os.path.isfile(thumbpath):
            try:
                os.remove(thumbpath)
            except Exception:
                pass

    def create_thumbnail(self, imgpath):
        """Create a thumbnail from the file at <path> and store it if it is
        larger than the defined thumbnail size.
        """
        try:
            img = self._get_thumbnail_image_from_source(imgpath)
        except ImageTooSmallException:
            return imgpath
        except:
            return None
        
        uri = self._path_to_uri(imgpath)
        thumbpath = self._uri_to_thumbpath(uri)
        mime = mimetypes.guess_type(imgpath)[0]
        stat = os.stat(imgpath)
        mtime = str(int(stat.st_mtime))
        size = str(stat.st_size)
        width = str(img.size[0])
        height = str(img.size[1])
        info = PngImagePlugin.PngInfo()
        info.add_text("Thumb::URI", uri)
        info.add_text("Thumb::MTime", mtime)
        info.add_text("Thumb::Size", size)
        if mime:
            info.add_text("Thumb::Mimetype", mime)
        info.add_text("Thumb::Image::Width", width)
        info.add_text("Thumb::Image::Height", height)
        info.add_text("Software", "Dinoteeth")
        try:
            tmppath = tempfile.mkstemp(".png","",self.basedir)[1]
            img.save(tmppath, pnginfo=info)
            os.rename(tmppath, thumbpath)
            os.chmod(thumbpath, 0600)
        except Exception:
            print '! thumbnail.py: Could not write', thumbpath, '\n'
            return None
        return thumbpath

    def _get_thumbnail_image_from_source(self, imgpath):
        raise RuntimeError("abstract method")
    
    def _path_to_uri(self, path):
        uri = 'file://' + pathname2url(os.path.abspath(path))
        return uri

    def _path_to_thumbpath(self, path):
        uri = self._path_to_uri(path)
        return self._uri_to_thumbpath(uri)

    def _uri_to_thumbpath(self, uri):
        """Return the full path to the thumbnail for <uri>.
        """
        md5hash = md5(uri).hexdigest()
        thumbpath = os.path.join(self.basedir, md5hash + '.png')
        return thumbpath


class ThumbnailFactory(AbstractThumbnailFactory):
    def _get_thumbnail_image_from_source(self, imgpath):
        """Create a thumbnail from the file at <path> and store it if it is
        larger than the defined thumbnail size.
        """
        img = Image.open(imgpath)
        if img.size[0] <= self.size[0] and img.size[1] <= self.size[1]:
            raise ImageTooSmallException
        try:
            img = self._get_rotated_thumbnail(img)
        except IOError:
            print "error thumbnailing %s" % imgpath
            raise
        return img

    def _get_rotated_thumbnail(self, img):
        """If image is rotated according to EXIF data, rotate the thumbnail
        before returning.
        
        http://www.impulseadventure.com/photo/exif-orientation.html
        """
        orientation = 1
        if hasattr(img, '_getexif'):
            try:
                exif = img._getexif()
                if exif != None and 0x0112 in exif:
                    orientation = exif[0x0112]
            except:
                pass
        img.thumbnail(self.size)
        
        if orientation == 6:
            img = img.transpose(Image.ROTATE_270)
        elif orientation == 3:
            img = img.transpose(Image.ROTATE_180)
        elif orientation == 8:
            img = img.transpose(Image.ROTATE_90)
        
        return img

class PygletThumbnailFactory(ThumbnailFactory):
    def get_image(self, imgpath):
        import pyglet
        
        thumbpath = self.get_thumbnail_file(imgpath)
        if thumbpath is not None:
            image = pyglet.image.load(thumbpath)
            return image
        return None


if __name__ == "__main__":
    from optparse import OptionParser
    usage="usage: %prog CMD [options] file [files...]"
    parser=OptionParser(usage=usage)
    parser.add_option("-v", action="store_true", dest="verbose", default=False)
    parser.add_option("-b", action="store", dest="base_dir", default=None)
    parser.add_option("-s", action="store", dest="size", type=int, default=128)
    parser.add_option("-i", action="store_true", dest="info", default=False)
    parser.add_option("-d", action="store_true", dest="delete", default=False)
    parser.add_option("-f", action="store", dest="from_file", default=None)
    (options, args) = parser.parse_args()

    factory = ThumbnailFactory(options.base_dir, options.size)
    thumbmap = {}
    
    if options.from_file:
        fh = open(options.from_file)
        for line in fh.readlines():
            path = line.strip()
            if path:
                rotate(path, options.rot, factory)
    
    def do(name):
        if options.delete:
            thumbpath = factory._path_to_thumbpath(name)
            print "%s -> %s" % (name, thumbpath)
            factory.delete_thumbnail(name)
        elif options.info:
            thumbpath = factory.get_thumbnail_file(name)
            print "%s -> %s" % (name, thumbpath)
            if thumbpath is not None:
                info = Image.open(thumbpath).info
                print info
        else:
            factory.create_thumbnail(name)
    
    def iter_dir(path):
        import glob
        
        names = glob.glob(os.path.join(path, "*"))
        for name in names:
            if os.path.isdir(name):
                print "dir %s" % name
                iter_dir(name)
            else:
                do(name)
    
    for name in args:
        if os.path.isdir(name):
            print "dir %s" % name
            iter_dir(name)
        else:
            do(name)
