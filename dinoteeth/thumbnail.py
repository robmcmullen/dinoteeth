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

class ThumbnailFactory(object):
    def __init__(self, basedir=None, size=128):
        if basedir is None:
            basedir = get_default_thumbnail_dir()
        self.basedir = basedir
        if not os.path.isdir(self.basedir):
            os.makedirs(self.basedir, 0700)
        if size <= 128:
            size = 128
        else:
            size = 256
        self.size = (size, size)
    
    def get_thumbnail_file(self, imgpath):
        """Return a thumbnail path for the file at <path> by looking in the
        directory of stored thumbnails.  If no thumbnail for <path> can be
        produced (for whatever reason), return None.
        """
        thumbpath = self._path_to_thumbpath(imgpath)
        if not os.path.exists(thumbpath):
            return self._create_thumbnail(imgpath)
        try:
            info = Image.open(thumbpath).info
            try:
                mtime = int(info['Thumb::MTime'])
            except Exception:
                mtime = -1
            if int(os.stat(imgpath).st_mtime) != mtime:
                return self._create_thumbnail(imgpath)
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

    def _create_thumbnail(self, imgpath):
        """Create a thumbnail from the file at <path> and store it if it is
        larger than the defined thumbnail size.
        """
        try:
            img = Image.open(imgpath)
        except:
            return None
        if img.size[0] <= self.size[0] and img.size[1] <= self.size[1]:
            return imgpath
        try:
            img = self._get_rotated_thumbnail(img)
        except IOError:
            print "error thumbnailing %s" % imgpath
            raise
        
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

class PygletThumbnailFactory(ThumbnailFactory):
    def get_image(self, imgpath):
        import pyglet
        
        thumbpath = self.get_thumbnail_file(imgpath)
        image = pyglet.image.load(thumbpath)
        return image


if __name__ == "__main__":
    f = ThumbnailFactory("../test/thumbnails/normal")
    print f.basedir
    t = f.get_thumbnail_file("../graphics/artwork-not-available.png")
    print t
    info = Image.open(t).info
    print info
    t = f.get_thumbnail_file("../graphics/background-merged.jpg")
    print t
    info = Image.open(t).info
    print info
    
