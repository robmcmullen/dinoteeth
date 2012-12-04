import os, sys, time, subprocess

from loader import Client

from mplayerlib import MPlayer
from .. import utils

class MPlayerClient(Client):
    def get_mplayer_opts(self, path):
        opts = self.settings.mplayer_opts.split()
        root, ext = os.path.splitext(path)
        # do something with path if desired
        return opts
    
    def play(self, media_file, resume_at=0.0, **kwargs):
        opts = self.get_mplayer_opts(media_file.pathname)
        self.audio_opts(opts, media_file.scan.selected_audio_id)
        self.subtitle_opts(opts, media_file.scan.selected_subtitle_id, media_file)
        if resume_at > 0:
            self.resume_opts(opts, resume_at)
        last_pos = self.play_slave(media_file.pathname, opts)
        return last_pos
    
    def play_file(self, pathname):
        opts = self.get_mplayer_opts(pathname)
        last_pos = self.play_slave(pathname, opts)
        return last_pos
    
    def audio_opts(self, opts, id):
        if id is not None:
            opts.extend(["-aid", str(id)])
    
    def subtitle_opts(self, opts, id, media_file):
        print "Subtitles: %s" % id
        if id is not None:
            if id < 0:
                opts.extend(["-noautosub", "-nosub"])
            else:
                if media_file.scan.is_subtitle_external(id):
                    path = media_file.scan.get_subtitle_path(id, media_file.pathname)
                    if path is not None:
                        opts.extend(["-sub", path])
                else:
                    opts.extend(["-sid", str(id)])
    
    def resume_opts(self, opts, last_pos):
        # Some fuzziness in mplayer when restarting (perhaps can only start on
        # I-frame?) so subtract some time and start from there.
        last_pos -= 10
        if last_pos > 0:
            opts.extend(["-ss", str(last_pos)])
    
    def play_slave(self, path, opts):
        last_pos = 0
        print("Playing: %s %s" % (path, str(opts)))
        try:
            mp = MPlayer(path, *opts)
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

Client.register("video", "*", MPlayerClient)
