#!/usr/bin/env python
"""Rip DVDs and encode to mkv

Requires:

dvdbackup
HandBrake CLI
"""

import os, sys, re, tempfile
import subprocess as sub
from optparse import OptionParser

def dprint(txt=""):
    print "-->%s<--" % txt.encode('utf-8')

def parseIntSet(nputstr=""):
    """Return list of integers from comma separated ranges
    
    Modified from http://thoughtsbyclayg.blogspot.com/2008/10/parsing-list-
    of-numbers-in-python.html to return ranges in order specified, rather than
    sorting the entire resulting list
    
    >>> parseIntSet("1,4,9-12")
    [1, 4, 9, 10, 11, 12]
    >>> parseIntSet("4,5,1,6")
    [4, 5, 1, 6]
    >>> parseIntSet("4,6-8,1,5,2")
    [4, 6, 7, 8, 1, 5, 2]
    """
    selection = []
    invalid = set()
    # tokens are comma seperated values
    tokens = [x.strip() for x in nputstr.split(',')]
    for i in tokens:
        try:
            # typically tokens are plain old integers
            selection.append(int(i))
        except:
            # if not, then it might be a range
            try:
               token = [int(k.strip()) for k in i.split('-')]
               if len(token) > 1:
                  token.sort()
                  # we have items seperated by a dash
                  # try to build a valid range
                  first = token[0]
                  last = token[len(token)-1]
                  for x in range(first, last+1):
                     selection.append(x)
            except:
               # not an int and not a range...
               invalid.add(i)
    # Report invalid tokens before returning valid selection
    if invalid:
        print "Invalid set: " + str(invalid)
    #ordered = list(selection)
    #ordered.sort()
    return selection


class ExeRunner(object):
    full_path_to_exe = None
    default_args = []
    
    def __init__(self, source, test_stdout=None, test_stderr=None, verbose=False, *args, **kwargs):
        self.verbose = verbose
        self.setCommandLine(source, *args, **kwargs)
        if test_stdout is not None or test_stderr is not None:
            self.testOutputProcessing(test_stdout, test_stderr)
        else:
            self.startExe()
    
    def verifyKeywordExists(self, key, kwargs):
        if key not in kwargs:
            kwargs[key] = []
    
    def prefixKeywordArgs(self, kwargs, key, *args):
        self.verifyKeywordExists(key, kwargs)
        current = list(*args)
        current.extend(kwargs[key])
        dprint(current)
        kwargs[key] = ",".join(current)

    def appendKeywordArgs(self, kwargs, key, *args):
        self.verifyKeywordExists(key, kwargs)
        current = kwargs[key]
        current.extend(*args)
        dprint(current)
        kwargs[key] = ",".join(current)

    def setCommandLine(self, source, *args, **kwargs):
        self.args = []
        if source is not None:
            self.args.append(source)
        if not args:
            args = self.default_args
        for arg in args:
            self.args.extend(arg.split())
        for key, value in kwargs.iteritems():
            self.args.append("-%s" % key)
            self.args.append(value)
    
    def startExe(self):
        args = [self.full_path_to_exe]
        args.extend(self.args)
        dprint(args)
        p = sub.Popen(args, stdout=sub.PIPE, stderr=sub.PIPE)
        stdout, stderr = p.communicate()
        self.parseOutput(stdout)
        self.parseErrors(stderr)
    
    def testOutputProcessing(self, stdout, stderr):
        if stdout is None:
            stdout = ""
        if stderr is None:
            stderr = ""
        self.parseOutput(stdout)
        self.parseErrors(stderr)
    
    def parseOutput(self, output):
        dprint(output)
    
    def parseErrors(self, output):
        #dprint(output)
        pass



class DVDBackup(ExeRunner):
    full_path_to_exe = "/usr/bin/dvdbackup"


class HandBrake(ExeRunner):
    full_path_to_exe = "/opt/src/HandBrake/build/HandBrakeCLI"

class Stream(object):
    def __init__(self, order):
        self.order = order
        self.id = -1
        self.lang = "unknown"
        self.threecc = "unk"

class Audio(Stream):
    def __init__(self, *args, **kwargs):
        Stream.__init__(self, *args, **kwargs)
        self.rate = -1
        self.bitrate = -1
        self.codec = ""

class Subtitle(Stream):
    def __init__(self, *args, **kwargs):
        Stream.__init__(self, *args, **kwargs)
        self.title = ""
        self.type = "vobsub"
    
    def __str__(self):
        return "subtitle #%d: id=%d %s %s %s" % (self.order, self.id, self.title, self.threecc, self.type)

class Title(object):
    def __init__(self, title_num):
        self.title_num = title_num
        self.main_feature = False
        self.vts = -1
        self.duration = 0
        self.size = ""
        self.pixel_aspect = ""
        self.display_aspect = ""
        self.fps = ""
        self.audio = []
        self.subtitle = []
    
    def find_audio(self, id):
        for audio in self.audio:
            if audio.id == id:
                return audio

class HandBrakeScanner(HandBrake):
    def setCommandLine(self, source, *args, **kwargs):
        args = list(args)
        args.extend(['--scan', '-i', source])
        HandBrake.setCommandLine(self, None, *args, **kwargs)
    
    def parseOutput(self, output):
        pass
    
    def parseErrors(self, output):
        self.num_titles = 0
        self.titles = []
        self.current_title = None
        self.current_stream = None
        stream_flag = None
        re_scan_num_title = re.compile("(\[.+\])? scan: DVD has (\d+) title")
        re_scan_title = re.compile("(\[.+\])? scan: scanning title (\d+)")
        re_audio = re.compile("(\[.+\])? scan: checking audio (\d+)")
        re_stream_id = re.compile("(\[.+\])? scan: id=0x([0-9a-f]+)bd, lang=(.+), 3cc=([a-z]+)")
        re_subtitle = re.compile("(\[.+\])? scan: checking subtitle (\d+)")
        re_preview = re.compile("(\[.+\])? scan: decoding previews for title (\d+)")
        re_preview_audio = re.compile("(\[.+\])? scan: audio 0x([0-9a-f]+)bd: (.+), rate=(\d+)Hz, bitrate=(\d+) (.+)")
        re_title_summary = re.compile("\+ title (\d+):")
        re_duration = re.compile("  \+ duration: (.+):")
        re_vts = re.compile("  \+ vts (\d+), ttn (\d+), (.+)")
        re_size = re.compile("  \+ size: (.+), pixel aspect: (.+), display aspect: ([\.\d]+), ([\.\d]+) fps")
        re_subtitle_type = re.compile("    \+ (\d+), (.+) \(iso639-2: ([a-z]+)\) (.+)")

        for line in output.splitlines():
            #dprint(line)
            match = re_scan_num_title.match(line)
            if match:
                self.num_titles = int(match.group(2))
                if self.verbose: print "matched! num titles=%d" % self.num_titles
                self.titles = [Title(i+1) for i in range(self.num_titles)]
                continue
            match = re_preview.match(line)
            if match:
                title = int(match.group(2))
                if self.verbose: print "matched! preview: title=%d" % title
                self.current_title = self.titles[title - 1]
                self.current_stream = None
                continue
            match = re_scan_title.match(line)
            if match:
                title = int(match.group(2))
                if self.verbose: print "matched! title=%d" % title
                self.current_title = self.titles[title - 1]
                self.current_stream = None
                continue
            match = re_title_summary.match(line)
            if match:
                title = int(match.group(1))
                if self.verbose: print "matched! + title=%d" % title
                self.current_title = self.titles[title - 1]
                self.current_stream = None
                self.stream_flag = ""
                continue
            if line.startswith("  + audio tracks"):
                stream_flag = "audio"
                continue
            if line.startswith("  + subtitle tracks"):
                stream_flag = "subtitle"
                continue
            if line.startswith("    +"):
                if stream_flag == "subtitle":
                    match = re_subtitle_type.match(line)
                    if match:
                        order = int(match.group(1))
                        try:
                            subtitle = self.current_title.subtitle[order - 1]
                        except IndexError:
                            # closed captioned subtitles aren't listed in
                            # earlier subtitle scans, so add it here.
                            subtitle = Subtitle(order)
                            self.current_title.subtitle.append(subtitle)
                        subtitle.title = match.group(2)
                        subtitle.threecc = match.group(3)
                        type = match.group(4).lower()
                        if "vobsub" in type:
                            subtitle.type = "vobsub"
                        elif "cc" in type and "text" in type:
                            subtitle.type = "cc"
                        else:
                            subtitle.type = "unknown"
                        if self.verbose: print subtitle
            
            if self.current_title:
                if line.startswith("  + Main Feature"):
                    if self.verbose: print "Main feature!"
                    self.current_title.main_feature = True
                    continue
                match = re_duration.match(line)
                if match:
                    self.current_title.duration = match.group(1)
                    if self.verbose: print "duration = %s" % self.current_title.duration
                    continue
                match = re_vts.match(line)
                if match:
                    self.current_title.vts = int(match.group(1))
                    if self.verbose: print "vts = %d" % self.current_title.vts
                    continue
                match = re_size.match(line)
                if match:
                    self.current_title.size = match.group(1)
                    self.current_title.pixel_aspect = match.group(2)
                    self.current_title.display_aspect = match.group(3)
                    self.current_title.fps = match.group(4)
                    if self.verbose: print "display aspect = %s" % self.current_title.display_aspect
                    continue
                match = re_audio.match(line)
                if match:
                    order = int(match.group(2))
                    if self.verbose: print "matched! audio=%d" % order
                    self.current_stream = Audio(order)
                    self.current_title.audio.append(self.current_stream)
                    continue
                match = re_preview_audio.match(line)
                if match:
                    id = int(match.group(2), 16)
                    if self.verbose: print "matched! preview audio=%d" % id
                    audio = self.current_title.find_audio(id)
                    audio.rate = int(match.group(4))
                    audio.bitrate = int(match.group(5))
                    audio.codec = match.group(6)
                    continue
                match = re_subtitle.match(line)
                if match:
                    order = int(match.group(2))
                    if self.verbose: print "matched! subtitle=%d" % order
                    self.current_stream = Subtitle(order)
                    self.current_title.subtitle.append(self.current_stream)
                    continue
            if self.current_stream:
                match = re_stream_id.match(line)
                if match:
                    id = int(match.group(2), 16)
                    if self.verbose: print "matched! id=%d" % id
                    self.current_stream.id = id
                    self.current_stream.lang = match.group(3)
                    self.current_stream.threecc = match.group(4)
                    continue


if __name__ == "__main__":
    usage="usage: %prog [options] file [files...]"
    parser=OptionParser(usage=usage)
    parser.add_option("-c", action="store_true", dest="crop", default=False, help="Crop detect test")
    parser.add_option("-i", action="store_true", dest="info", default=False, help="Only print info")
    parser.add_option("-d", action="store", dest="device", default='/dev/dvd', help="Title")
    parser.add_option("-t", action="store", dest="title", default='', help="Title")
    parser.add_option("-e", action="store", type="int", dest="episode", default=-1, help="Starting episode number")
    parser.add_option("-x", action="store", type="int", dest="extra", default=-1, help="Starting extra feature number")
    parser.add_option("-s", action="store", type="int", dest="season", default=-1, help="Season number")
    parser.add_option("--all", action="store_true", dest="all", default=False, help="Rip all tracks")
    parser.add_option("--subtitles-only", action="store_true", dest="subtitles_only", default=False, help="Rip only subtitles from a previously ripped vob")
    parser.add_option("--stdout", action="store", default=None, help="File containing test stdout")
    parser.add_option("--stderr", action="store", default=None, help="File containing test stderr")
    (options, args) = parser.parse_args()

