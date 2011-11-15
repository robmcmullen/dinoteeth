import os, sys, glob, time

import pyglet

from mplayerlib import MPlayer
from model import Menu
from media import MediaDetail, MovieTitle
import utils

class MPlayerDetail(MediaDetail):
    def __init__(self, title):
        MediaDetail.__init__(self, title.pathname, title)
        
    def play(self, conf):
        escaped_path = utils.shell_escape_path(self.fullpath)
        opts = conf.get_mplayer_opts(self.fullpath)
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
