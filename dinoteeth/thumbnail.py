"""Common cache for thumbnails described at:

http://people.freedesktop.org/~vuntz/thumbnail-spec-cache/

This imprementation is reworked from http://sourceforge.net/projects/comix/ to
support PIL rather than GTK for image creation.

Original GPL source: http://comix.svn.sourceforge.net/viewvc/comix/trunk/src/thumbnail.py?revision=321&view=markup
"""

import os, tempfile, mimetypes, subprocess
from cStringIO import StringIO
from urllib import pathname2url, url2pathname
from hashlib import md5

from PIL import Image, PngImagePlugin


def get_home_dir():
    return os.path.expanduser("~")

def get_home_subdir(relpath):
    return os.path.join(get_home_dir(), relpath)

def get_default_thumbnail_dir(size):
    if size <= 128:
        subdir = "normal"
    elif size <= 256:
        subdir = "large"
    elif size <= 512:
        subdir = "video"
    return get_home_subdir(".thumbnails/%s" % subdir)

class ImageTooSmallException(RuntimeError):
    pass

class AbstractThumbnailFactory(object):
    def __init__(self, basedir=None, size=128):
        if size <= 128:
            size = 128
        elif size <= 256:
            size = 256
        else:
            size = 512
        self.size = (size, size)
        if not basedir:
            basedir = get_default_thumbnail_dir(size)
        self.basedir = basedir
        if not os.path.isdir(self.basedir):
            os.makedirs(self.basedir, 0700)
    
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
            if not self._is_current(imgpath, thumbpath):
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


class ImageThumbnailFactory(AbstractThumbnailFactory):
    def _is_current(self, imgpath, thumbpath):
        info = Image.open(thumbpath).info
        try:
            mtime = int(info['Thumb::MTime'])
        except Exception:
            mtime = -1
        if int(os.stat(imgpath).st_mtime) != mtime:
            return False
        return True
        
    def _get_thumbnail_image_from_source(self, imgpath):
        """Create a thumbnail from the file at <path> and store it if it is
        larger than the defined thumbnail size.
        """
        img = Image.open(imgpath)
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
        if img.size[0] > self.size[0] or img.size[1] > self.size[1]:
            img.thumbnail(self.size)
        
        if orientation == 6:
            img = img.transpose(Image.ROTATE_270)
        elif orientation == 3:
            img = img.transpose(Image.ROTATE_180)
        elif orientation == 8:
            img = img.transpose(Image.ROTATE_90)
        
        return img

arrow = '\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00V\x00\x00\x00;\x08\x06\x00\x00\x00\xe1<}s\x00\x00\x00\x01sRGB\x00\xae\xce\x1c\xe9\x00\x00\x00\x06bKGD\x00\x00\x00\x00\x00\x00\xf9C\xbb\x7f\x00\x00\x00\tpHYs\x00\x00\x0b\x13\x00\x00\x0b\x13\x01\x00\x9a\x9c\x18\x00\x00\x00\x07tIME\x07\xdc\x04\x10\x136\x15\xf6\x10\xef\x1c\x00\x00\x00\x1diTXtComment\x00\x00\x00\x00\x00Created with GIMPd.e\x07\x00\x00\x03\x06IDATx\xda\xed\xdc\xcdJ\x1bQ\x14\x07\xf0\xf9\x88\x8b8\x1d\xb7\xb5h\n\x12\x10;\xa8\xddd\xe2 \xc1T\xa4A\x1a\x08\x89h!\xd8\xc1\x9d\x11\x14\x02\xbe@q\xa5\x0f \xd9I\x9a\xc4\xb6\x10\x99\x8d\xd0J\xab\x16*&1q#\x86$\x8bQ*\x8d\x8b\x16+\x16lB\xe3\x98N_\xe2Nf\xee\xcd\xf9\xbf\xc0=\xf3[\xdc3\xe7L\x08MQ\xd4k\n\x82<\x0c\x10\x00,\xc0B\x00\x96\\\xd8X,&\x02\xac\x01\x91e\xd9\x9b\xcdfC\x1d\x1d\x1d\x0c\xc0"\xce\xd0\xd0\x90\xf3\xe2\xe2"\xd2\xdf\xdf\xcf\x01,\xe2tuuq\xf9|~>\x14\nu\x03,\xe2\xd8l66\x99L\xbe\x8a\xc5bn\x805\xe6\xde\x1d\xdb\xdb\xdb\xf3\xb3,K\x03,\xe2\x8c\x8c\x8c<)\x16\x8b\xb3\x1c\xc7\xb1\x00\x8b8\x0e\x87\xa3[UU,\x9b\x9a\xe5_qx\x9e\xef<>>^XZZr\x02,\xea"\x19\x86^]]\r\xc5\xe3\xf1Q\x805 \xd3\xd3\xd3\xa3\'\'\'a\xbb\xdd\xce\x02,\xe28\x9d\xce\x9e\xf3\xf3\xf3y\xab\xdf\xbbX\x8e\x91<\xcfs\x85Ba~jj\xea\x11\xc0"\x0e\xcb\xb2l"\x91\x98\xb5\xea0\x81\xfd\xe2C\x96\xe5\xb1\x9d\x9d\x9dI\x805 \x1e\x8fg\xb0R\xa9\xc8<\xcf\xdb\x00\x16qz{{\x1f\xaa\xaa\x1a\x11\x04\xe1\x01\xc0"\x0e\xc7q\xf6\xa3\xa3\xa3\x85\x95\x95\x95A\x80E\x1c\x9a\xa6\xa9\xe5\xe5\xe5\xc9T*\xe5\x01X\x03\x12\x0c\x06\xa5\xd3\xd3\xd3\xb0YK\x1c\xa2?&\xf6\xf5\xf5\xf5\xa8\xaa\x1a\x19\x18\x18\xe0\x00\x16\xfd0\xd1\x99\xcf\xe7#sss\x8f\x01\x16\xf5C2\x0c\xb3\xbe\xbe\xfermm\xed)\xc0\x1a\x90\xc5\xc5\xc5\xe7\xbb\xbb\xbb/Z\xf1e\xa2\xed~\xb0!I\x92\xb0\xbd\xbd\xed\x03X\xc4)\x14\n\x95@ \xf0\x19`\x11FQ\x94\xdc\xc4\xc4\xc4\x87f\xb3\xa9\x1b}\x96\xad\x1d@u]\xd7\xa3\xd1\xe8V<\x1e\xff\xde\xaa3\x89\x87m4\x1aw\x81@ \x95\xcdfoZy.\xd1\xb0\xd7\xd7\xd7\xbfEQL^]]\xdd\xb5\xfalba\xcf\xce\xce\xaan\xb7{K\xd3\xb4\x7f0\xd2"J.\x97+\xbb\\\xae\xb4Y\xa8D\xc2nll|\xf1\xf9|\x1f[\xd1\xf9\xdb\xe2*\xd04\xed~fffs\x7f\x7f\xff\x97\x15\xea!\x02\xb6^\xaf\xff\x1d\x1f\x1f\x7fS.\x97\xffX\xa5&\xeca///\x7f\xba\\\xaew\xb5Z\xadi\xa5\xba\xb0\xbecK\xa5\xd2\xb7\xe1\xe1\xe1\xb7VC\xc5\x1a6\x9dNg$IR\xcc\xec\xfcD]\x05f\x8c\xa7\xc4\xc36\x1a\r-\x18\x0c&\x0f\x0f\x0fo\xac^+6\xb0\xb7\xb7\xb75\xaf\xd7\x9bPU\xb5\x8eC\xbdX\xc0V\xab\xd5\x1f\xa2(\xbe\xb7b\x93\xc2\xb6y\x1d\x1c\x1c\x14\x05A\xd8\xc4\t\xd5\xf2\xb0\x8a\xa2\xe4\xfc~\xff\'\x1c\xdfZ,y\x15\xe0\xd2\xf9\xb1\x825k1M4\xac\x99\x8biba\xcd^L\x13\xd9\xbc2\x99L\xc9\xec\xc54\xea\xb0\x14E=3\xb3\x00\x87\xc3q\x1f\x0e\x87\xbf\xea\xbaN\x91\x14\x9a\x82\xbf\x87j\xcf\x01\x01`!\x00\xdb\x8a\xfc\x07U\xc0/ou/\x18!\x00\x00\x00\x00IEND\xaeB`\x82'

class VideoThumbnailFactory(AbstractThumbnailFactory):
    def __init__(self, basedir=None, size=512):
        AbstractThumbnailFactory.__init__(self, basedir, size)
    
    def create_thumbnail(self, imgpath):
        """Create a thumbnail from the file at <path> and store it if it is
        larger than the defined thumbnail size.
        """
        uri = self._path_to_uri(imgpath)
        thumbpath = self._uri_to_thumbpath(uri)
        
        tmppath = tempfile.mkstemp(".png","",self.basedir)[1]
        args = ["ffmpegthumbnailer", "-i", imgpath, "-o", tmppath, "-s", str(self.size[0])]
        p = subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        output, errors = p.communicate()
        
        img = Image.open(tmppath)
        layer = Image.new('RGBA', img.size, (0,0,0,0))
        watermark = Image.open(StringIO(arrow))
        layer.paste(watermark, (img.size[0] - watermark.size[0] - 16,
                                img.size[1] - watermark.size[1] - 16))
        img = Image.composite(layer, img, layer)
        img.save(thumbpath)
        os.remove(tmppath)

    def _is_current(self, imgpath, thumbpath):
        return os.path.getmtime(thumbpath) > os.path.getmtime(imgpath)

    def _uri_to_thumbpath(self, uri):
        """Return the full path to the thumbnail for <uri>.
        
        JPEG thumbnails for videos!
        """
        md5hash = md5(uri).hexdigest()
        thumbpath = os.path.join(self.basedir, md5hash + '.jpg')
        return thumbpath


class ThumbnailFactory(object):
    def __init__(self, local_basedir=None, shared_basedir=None, image_size=128, video_size=512):
        self.image = ImageThumbnailFactory(local_basedir, image_size)
        self.shared_basedir = shared_basedir
        if shared_basedir is not None:
            thumbnail_dir = os.path.join(shared_basedir, "thumbnails")
            self.image_shared = ImageThumbnailFactory(thumbnail_dir, image_size)
        self.video = VideoThumbnailFactory(local_basedir, video_size)
    
    def which(self, imgpath):
        ext = os.path.splitext(imgpath)[1].lower()
        if ext in [".jpg", ".png", ".gif"]:
            if self.shared_basedir and imgpath.startswith(self.shared_basedir):
                return self.image_shared
            return self.image
        return self.video
    
    def create_thumbnail(self, imgpath, *args, **kwargs):
        which = self.which(imgpath)
        return which.create_thumbnail(imgpath, *args, **kwargs)
    
    def delete_thumbnail(self, imgpath, *args, **kwargs):
        which = self.which(imgpath)
        return which.delete_thumbnail(imgpath, *args, **kwargs)
    
    def get_thumbnail_file(self, imgpath, *args, **kwargs):
        which = self.which(imgpath)
        return which.get_thumbnail_file(imgpath, *args, **kwargs)
    
    def _path_to_thumbpath(self, imgpath):
        which = self.which(imgpath)
        return which._path_to_thumbpath(imgpath)


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

    factory = ThumbnailFactory(options.base_dir, image_size=options.size, video_size=512)
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
