import os, re, time

from common import *
from parser import HandBrakeScanParser

from ..utils import vprint

class HandBrakeScanner(HandBrake):
    default_scanfile = "handbrake.scan"
    
    def __str__(self):
        lines = []
        too_short = 0
        for title in self.iter_titles():
            if title.num_minutes() >= self.min_time:
                size = [int(t) for t in title.size.split("x")]
                if title.autocrop != "0/0/0/0":
                    crop = [int(t) if int(t) > 2 else 0 for t in title.autocrop.split("/")]
                    vf = "-vf crop=%d:%d:%d:%d" % (size[0] - crop[2] - crop[3],
                                                   size[1] - crop[0] - crop[1],
                                                   crop[2], crop[0])
                else:
                    vf = ""
                lines.append("mplayer %s %s" % (title.mplayer_cmd(self.source), vf))
                lines.append(str(title))
            else:
                too_short += 1
        if too_short > 0:
            lines.append("%d other titles less than %d minutes" % (too_short, self.min_time))
        return "\n".join(lines)

    def setCommandLine(self, source, options=None, *args, **kwargs):
        self.source = source
        self.parseOptions(options)
        args = list(args)
        args.extend(['--scan', '-t', '0'])
        HandBrake.setCommandLine(self, source, *args, **kwargs)
    
    @classmethod
    def get_scanfile(cls, source):
        if os.path.isdir(source):
            scanfile = os.path.join(source, cls.default_scanfile)
        else:
            dirname, basename = os.path.split(source)
            scanfile = os.path.join(dirname, basename + "." + cls.default_scanfile)
        return scanfile
    
    def parseOptions(self, options):
        self.preferred_lang = options.lang
        self.min_time = options.min_time
        self.scanfile = options.scanfile
        if self.scanfile:
            self.scanfile = self.get_scanfile(self.source)
    
    def run(self):
        vprint(0, "-Running HandBrake --scan %s" % self.source)
        if self.scanfile:
            if os.path.exists(self.scanfile):
                vprint(0, "--Using previous scan %s" % self.scanfile)
                fh = open(self.scanfile)
                previous_run = fh.read()
                self.parseErrors(previous_run)
                return
        HandBrake.run(self)

    def parseOutput(self, output):
        pass
    
    def parseErrors(self, output):
        if self.scanfile:
            if not os.path.exists(self.scanfile):
                fh = open(self.scanfile, "w")
                fh.write(output)
                fh.close()
                
        self.num_titles = 0
        self.titles = {}
        
        parser = HandBrakeScanParser.identify(output)
        parser.parse_into(self)
        self.create_user_title_map()
    
    def create_user_title_map(self):
        # The directory parser of HandBrake orders titles based on raw
        # directory order which is non-deterministic.  Restructure a title map
        # based on the user title number to create determinism.
        self.user_title_num_map = {}
        for t in self.titles.values():
            self.user_title_num_map[t.user_title_num] = t
    
    def get_user_title(self, title_num):
        return self.user_title_num_map[title_num]
    
    def iter_titles(self):
        d = [(t.user_title_num, t) for t in self.titles.values()]
        d.sort()
        for _, title in d:
            yield title
    
    def get_title(self, title_num):
        if title_num not in self.titles:
            self.titles[title_num] = Title(title_num, self)
        return self.titles[title_num]
#        if title_num > len(self.titles):
#            for i in range(len(self.titles), title_num):
#                self.titles.append(Title(i+1, self))
#            self.num_titles = len(self.titles)
#        return self.titles[title_num - 1]
