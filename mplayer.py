import os, sys, glob, time

import pyglet

from mplayerlib import MPlayer

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
