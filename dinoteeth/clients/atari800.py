import os, sys, time, subprocess

from loader import Client

class Atari800Client(Client):
    def get_args(self, path):
        args = []
        prog = self.settings.atari800_prog
        args.append(prog)
        opts = self.settings.atari800_opts.split()
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

Client.register("game", "atari-8bit", Atari800Client)
