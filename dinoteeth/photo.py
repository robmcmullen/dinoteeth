import os, sys, glob, logging, subprocess

import utils

from model import MenuItem, MenuPopulator
from updates import UpdateManager

log = logging.getLogger("dinoteeth.photo")

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
    def iter_create(self):
        yield "By Folder", PhotoFolderLookup(self.config)
        yield "Slideshows", SlideshowLookup(self.config)

    def get_metadata(self):
        return {
            'imagegen': self.thumbnail_mosaic,
            }

class PhotoFolderLookup(MenuPopulator):
    def iter_create(self):
        db = self.config.get_photo_database()
        for path in db.paths:
            yield utils.decode_title_text(os.path.basename(path)), PhotoFolder(self.config, path)

    def get_metadata(self):
        return {
            'imagegen': self.thumbnail_mosaic,
            }

class PhotoFolder(MenuPopulator):
    def __init__(self, config, path):
        MenuPopulator.__init__(self, config)
        self.path = path
    
    def iter_create(self):
        dirs = glob.glob(os.path.join(self.path, "*"))
        dirs.sort()
        for path in dirs:
            if os.path.isdir(path):
                files = glob.glob(os.path.join(path, "*"))
                pictures = [f for f in files if os.path.splitext(f)[1].lower() in Pictures.valid_image_types]
                videos = [f for f in files if os.path.splitext(f)[1].lower()[1:] in self.config.get_video_extensions()]
                if pictures:
                    yield utils.decode_title_text(os.path.basename(path)), Pictures(self.config, path)
                if videos:
                    yield utils.decode_title_text(os.path.basename(path)) + " (videos)", HomeVideos(self.config, videos)
                if not pictures and not videos:
                    subdirs = [d for d in files if os.path.isdir(d)]
                    if subdirs:
                        yield utils.decode_title_text(os.path.basename(path)) + " (folders)", PhotoFolder(self.config, path)

class Pictures(MenuPopulator):
    valid_image_types = ['.jpg', '.png', '.gif']
    
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

    def play(self, config=None):
        self.config.prepare_for_external_app()
        log.debug("Starting slideshow for %s" % self.path)
        args = [sys.executable, "bin/slideshow.py", "--once", self.path]
        p = subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        output, errors = p.communicate()
        self.config.restore_after_external_app()
    
    def get_mosaic_size(self):
        return 140, 140

    def get_metadata(self):
        return {
            'imagegen': self.thumbnail_mosaic,
            }

class HomeVideos(MenuPopulator):
    def __init__(self, config, videos):
        MenuPopulator.__init__(self, config)
        self.videos = videos
        self.videos.sort()
    
    def iter_image_path(self, artwork_loader):
        for video in self.videos:
            yield video
    
    def get_thumbnail(self, imgpath, thumbnail_factory):
        # Need to get a thumbnail of the video thumbnail, not the thumbnail of
        # the video!  Very 'Inception', I know.
        video_thumb = thumbnail_factory.get_thumbnail_file(imgpath)
        if video_thumb is None:
            # Large video thumbnail must be created first
            UpdateManager.create_thumbnail(imgpath)
            return None
        try:
            thumb_image = thumbnail_factory.get_image(video_thumb)
        except Exception, e:
            log.debug("Skipping failed thumbnail %s: %s" % (video_thumb, e))
            return None
        if thumb_image is None:
            # If the thumbnail of the video thumb doesn't exist, 
            UpdateManager.create_thumbnail(video_thumb)
        return thumb_image
    
    def get_mosaic_size(self):
        return 140, 140
    
    def iter_create(self):
        for video in self.videos:
            yield utils.decode_title_text(os.path.basename(video)), HomeVideoPlay(self.config, video)

    def get_metadata(self):
        return {
            'imagegen': self.thumbnail_mosaic,
            }

class HomeVideoPlay(MenuPopulator):
    def __init__(self, config, video):
        MenuPopulator.__init__(self, config)
        self.video = video

    def play(self, config=None):
        self.config.prepare_for_external_app()
        client = self.config.get_media_client()
        log.debug("Starting video for %s" % self.video)
        last_pos = client.play_file(self.video)
        self.config.restore_after_external_app()
    
    def get_metadata(self):
        return {
            'imagegen': self.video_detail,
            }

    def video_detail(self, artwork_loader, thumbnail_factory, x, y, w, h):
        image = thumbnail_factory.get_image(self.video)
        image.blit(x, h - image.height, 0)


class SlideshowLookup(MenuPopulator):
    def iter_create(self):
        db = self.config.get_photo_database()
        for path in db.paths:
            yield path, PhotoFolder(self.config, path)
