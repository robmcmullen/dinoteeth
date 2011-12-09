import os, sys, time, subprocess

from mplayerlib import MPlayer
import utils
from media import AudioTrack, SubtitleTrack

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
            mp.quit()
        return last_pos


class MPlayerInfo(object):
    identify_args = ["-vo", "null", "-ao", "null", "-identify", "-frames", "0"]
    
    def __init__(self, filename, *opts):
        self.filename = filename
        args = [MPlayer.exe_name]
        args.extend(self.identify_args)
        if opts:
            args.extend(opts)
        args.append(filename)
        p = subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        output, errors = p.communicate()
        self.process_output(output)
    
    def process_output(self, output):
        self.output = output
        self.audio_order = []
        self.audio = {}
        self.subtitles_order = []
        self.subtitles = {}
        current = {'subtitle': None,
                   'audio': None,
                   }
        for line in output.splitlines():
            if line.startswith("ID_"):
                key, value = line.split("=", 1)
                if value.startswith("\"") and value.endswith("\""):
                    value = value[1:-1]
                setattr(self, key, value)
                if key == "ID_AUDIO_ID":
                    id = int(value)
                    self.audio_order.append(id)
                    current['audio'] = AudioTrack(id)
                    self.audio[id] = current['audio']
                if key == "ID_SUBTITLE_ID":
                    id = int(value)
                    self.subtitles_order.append(id)
                    current['subtitle'] = SubtitleTrack(id)
                    self.subtitles[id] = current['subtitle']
                self.process_details(key, value, current['audio'], "ID_AID_")
                self.process_details(key, value, current['subtitle'], "ID_SID_")
        self.normalize()
    
    def normalize(self):
        if hasattr(self, "ID_LENGTH"):
            self.length = float(self.ID_LENGTH)
        else:
            self.length = 0.0
    
    def process_details(self, key, value, track, key_root):
        if track and key.startswith(key_root):
            root = "%s%d_" % (key_root, track.id)
            try:
                _, subkey = key.split(root)
                if subkey == "NAME":
                    track.name = value
                elif subkey == "LANG":
                    track.lang = value
            except ValueError:
                pass
    
    def iter_audio(self):
        for id in self.audio_order:
            yield self.audio[id]
    
    def iter_subtitles(self):
        for id in self.subtitles_order:
            yield self.subtitles[id]
    
