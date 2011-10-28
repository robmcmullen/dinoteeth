import os, sys, glob, time

import pyglet

from mplayerlib import MPlayer
from model import Menu


class MPlayerMenu(Menu):
    def __init__(self, config, pathname):
        Menu.__init__(self, "", config)
        self.fullpath = pathname
        self.dirname, self.filename = os.path.split(pathname)
        self.fileroot, self.fileext = os.path.splitext(self.filename)
        self.title = self.config.decode_title_text(self.fileroot)
        self.detail_image = None
        self.playable = True
    
    def __cmp__(self, other):
        return cmp(self.title, other.title)
    
    # Overriding get_detail_image to perform lazy image lookup 
    def get_detail_image(self):
        if self.detail_image is None:
            imagedir = os.path.join(self.dirname, ".thumbs")
            for ext in [".jpg", ".png"]:
                imagepath = os.path.join(imagedir, self.fileroot + ext)
                print "checking %s" % imagepath
                if os.path.exists(imagepath):
                    self.detail_image = pyglet.image.load(imagepath)
                    print "loaded %s" % imagepath
                    break
            if self.detail_image is None:
                self.detail_image = self.config.get_default_poster()
        return self.detail_image
    
    # Placeholder for IMDB lazy lookup
    def get_details(self):
        return "Details for %s" % self.title
    
    def play(self):
        escaped_path = self.config.shell_escape_path(self.fullpath)
        opts = self.config.get_mplayer_opts(self.fullpath)
        last_pos = self.play_slave(escaped_path, opts)
    
    def play_slave(self, escaped_path, opts):
        last_pos = 0
        print("Playing: %s %s" % (escaped_path, str(opts)))
        try:
            mp = MPlayer(escaped_path, *opts)
            while mp._is_running():
                try:
                    last_pos = mp._get_current_pos()
                except:
                    # don't reset the last good value on an exception
                    pass
                time.sleep(1)
        except:
            print("Couldn't start movie!")
            raise
        finally:
            print dir(mp)
            mp.quit()
        return last_pos


class MovieParser(object):
    video_extensions = ['.vob', '.mp4', '.avi', '.wmv', '.mov', '.mpg', '.mpeg', '.mpeg4', '.mkv', '.flv']
    exclude = []
    verbose = True
    
    @classmethod
    def add_videos_in_path(cls, menu, config, path):
        videos = glob.glob(os.path.join(path, "*"))
        for video in videos:
            valid = False
            if os.path.isdir(video):
                if not video.endswith(".old"):
                    if self.exclude:
                        match = cls.exclude.search(video)
                        if match:
                            if cls.verbose: print("Skipping dir %s" % video)
                            continue
                    print("Checking dir %s" % video)
                    cls.add_videos_in_path(menu, config, video)
            elif os.path.isfile(video):
                print("Checking %s" % video)
                for ext in cls.video_extensions:
                    if video.endswith(ext):
                        valid = True
                        print ("Found valid media: %s" % video)
                        break
                if valid:
                    cls.add_video(menu, config, video)
        menu.sort_items()
    
    @classmethod
    def add_video(cls, menu, config, filename):
        """Check to see if the filename is associated with a series
        """
        video = MPlayerMenu(config, filename)
        menu.add_item(video)
