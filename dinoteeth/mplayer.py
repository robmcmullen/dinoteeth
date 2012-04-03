import os, sys, time, subprocess

from mplayerlib import MPlayer
import utils

class MPlayerClient(object):
    def __init__(self, config):
        self.config = config
        
    def play(self, media_scan, resume_at=0.0):
        escaped_path = utils.shell_escape_path(media_scan.pathname)
        opts = self.config.get_mplayer_opts(media_scan.pathname)
        self.audio_opts(opts, media_scan.selected_audio_id)
        self.subtitle_opts(opts, media_scan.selected_subtitle_id)
        if resume_at > 0:
            self.resume_opts(opts, resume_at)
        last_pos = self.play_slave(escaped_path, opts)
        return last_pos
    
    def audio_opts(self, opts, id):
        if id is not None:
            opts.extend(["-aid", str(id)])
    
    def subtitle_opts(self, opts, id):
        print "Subtitles: %s" % id
        if id is not None:
            if id < 0:
                opts.extend(["-noautosub", "-nosub"])
            else:
                opts.extend(["-sid", str(id)])
    
    def resume_opts(self, opts, last_pos):
        # Some fuzziness in mplayer when restarting (perhaps can only start on
        # I-frame?) so subtract some time and start from there.
        last_pos -= 10
        if last_pos > 0:
            opts.extend(["-ss", str(last_pos)])
    
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
            mp.quit()
        return last_pos
