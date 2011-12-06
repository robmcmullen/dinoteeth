import os, sys, time

from mplayerlib import MPlayer
import utils

class MPlayerClient(object):
    def __init__(self, config):
        self.config = config
        
    def play(self, path, audio=None, subtitle=None):
        escaped_path = utils.shell_escape_path(path)
        opts = self.config.get_mplayer_opts(path)
        last_pos = self.play_slave(escaped_path, opts)
        return last_pos
    
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
