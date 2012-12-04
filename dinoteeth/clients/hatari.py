import os, sys, time, subprocess

from loader import Client

# Hatari documentation: http://hg.tuxfamily.org/mercurialroot/hatari/hatari/raw-file/tip/doc/manual.html
#
# Config file entry to provide filename to save on exit:
#
# [Memory]
# nMemorySize = 1
# bAutoSave = TRUE
# szMemoryCaptureFileName = /path/to/save/game.hatari
# szAutoSaveFileName = /path/to/save/game.hatari
#
# start using: hatari -c /path/to/config.cfg
#
# Info on saving state on exit using F12 key: http://www.atari-forum.com/viewtopic.php?f=51&t=22422 
#
# "changed all [ShortcutsWithoutModifiers] in the cfg to 0 exept KeyQuit.
# Changed it to "keyQuit = 293" F12 is quit and you need the alt tab to go to
# other options."

class HatariClient(Client):
    def get_args(self, path):
        args = []
        prog = self.settings.hatari_prog
        args.append(prog)
        opts = self.settings.hatari_opts.split()
        args.extend(opts)
        
        root, ext = os.path.splitext(path)
        # do something with path if desired
        
        args.append(path)
        return args
    
    def play(self, media_file, resume_at=0.0, **kwargs):
        args = self.get_args(media_file.pathname)
        print args
        proc = subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        stdout, stderr = proc.communicate()
        if stdout:
            print("stdout: %s" % stdout)
        if stderr:
            print("stderr: %s" % stderr)

Client.register("game", "atari-st", HatariClient)
