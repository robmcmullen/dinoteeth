#!/usr/bin/env python
"""Rip DVDs and encode to mkv

Requires:

dvdbackup
HandBrake CLI
"""

import os, sys, re, tempfile
import subprocess as sub
sys.path.insert(0, "..") # to find third_party
try:
    import argparse
except:
    import third_party.argparse as argparse
from utils import encode_title_text, canonical_filename

def dprint(txt=""):
    if not isinstance(txt, basestring):
        txt = str(txt)
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

# lexical token symbols
DQUOTED, SQUOTED, UNQUOTED, COMMA, NEWLINE = xrange(5)

_pattern_tuples = (
    (r'"[^"]*"', DQUOTED),
    (r"'[^']*'", SQUOTED),
    (r",", COMMA),
    (r"$", NEWLINE), # matches end of string OR \n just before end of string
    (r"[^,\n]+", UNQUOTED), # order in the above list is important
    )
_matcher = re.compile(
    '(' + ')|('.join([i[0] for i in _pattern_tuples]) + ')',
    ).match
_toktype = [None] + [i[1] for i in _pattern_tuples]
# need dummy at start because re.MatchObject.lastindex counts from 1 

def csv_split(text):
    """Split a csv string into a list of fields.
    Fields may be quoted with " or ' or be unquoted.
    An unquoted string can contain both a " and a ', provided neither is at
    the start of the string.
    A trailing \n will be ignored if present.
    
    From http://stackoverflow.com/questions/4982531/how-do-i-split-a-comma-delimited-string-in-python-except-for-the-commas-that-are
    """
    fields = []
    pos = 0
    want_field = True
    while 1:
        m = _matcher(text, pos)
        if not m:
            raise ValueError("Problem at offset %d in %r" % (pos, text))
        ttype = _toktype[m.lastindex]
        if want_field:
            if ttype in (DQUOTED, SQUOTED):
                fields.append(m.group(0)[1:-1])
                want_field = False
            elif ttype == UNQUOTED:
                fields.append(m.group(0))
                want_field = False
            elif ttype == COMMA:
                fields.append("")
            else:
                assert ttype == NEWLINE
                fields.append("")
                break
        else:
            if ttype == COMMA:
                want_field = True
            elif ttype == NEWLINE:
                break
            else:
                print "*** Error dump ***", ttype, repr(m.group(0)), fields
                raise ValueError("Missing comma at offset %d in %r" % (pos, text))
        pos = m.end(0)
    return fields

class ExeRunner(object):
    full_path_to_exe = None
    default_args = []
    
    def __init__(self, source, options=None, test_stdout=None, test_stderr=None, verbose=False, *args, **kwargs):
        self.verbose = verbose
        self.setCommandLine(source, options=options, *args, **kwargs)
        if test_stdout is not None or test_stderr is not None:
            self.testOutputProcessing(test_stdout, test_stderr)
    
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
    
    def run(self):
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

    def setCommandLine(self, source, options=None, *args, **kwargs):
        args = list(args)
        args.extend(['-i', source])
        ExeRunner.setCommandLine(self, None, *args, **kwargs)

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
    
    def __str__(self):
        return "audio #%d: id=%d %s %s %dkHz %dkbps %s" % (self.order, self.id, self.threecc, self.lang, self.rate/1000, self.bitrate/1000, self.codec)

class Subtitle(Stream):
    def __init__(self, *args, **kwargs):
        Stream.__init__(self, *args, **kwargs)
        self.title = ""
        self.type = "vobsub"
    
    def __str__(self):
        return "subtitle #%d: id=%d %s %s %s" % (self.order, self.id, self.title, self.threecc, self.type)

class Title(object):
    def __init__(self, title_num, handbrake):
        self.title_num = title_num
        self.handbrake = handbrake
        self.main_feature = False
        self.vts = -1
        self.duration = "00:00:00"
        self.size = ""
        self.pixel_aspect = ""
        self.display_aspect = ""
        self.fps = ""
        self.audio = []
        self.subtitle = []
    
    def __str__(self):
        s = "title %d: %s " % (self.title_num, self.duration)
        if self.main_feature:
            s += "(MAIN) "
        s += "%s, %s " % (self.size, self.display_aspect)
        s += "%d audio " % (len(self.audio))
        pref = 0
        extra = ""
        selected = self.find_audio_by_language()
        for a in selected:
            pref += 1
            extra += " " + str(a) + "\n"
        if pref > 0:
            s += "(%d %s) " % (pref, self.handbrake.preferred_lang)
        s += "%d subtitles " % (len(self.subtitle))
        pref = 0
        selected = self.find_subtitle_by_language()
        for a in selected:
            pref += 1
            extra += " " + str(a) + "\n"
        if pref > 0:
            s += "(%d %s) " % (pref, self.handbrake.preferred_lang)
        if extra:
            s += "\n" + extra
        return s
    
    def num_minutes(self):
        t = self.duration.split(":")
        minutes = int(t[0])*60 + int(t[1])
        return minutes
    
    def find_audio(self, id):
        for audio in self.audio:
            if audio.id == id:
                return audio
    
    def find_stream_by_language(self, stream, lang=None):
        if lang is None:
            lang = self.handbrake.preferred_lang
        selected = []
        for s in stream:
            if s.threecc == lang:
                selected.append(s)
        return selected
    
    def find_audio_by_language(self, lang=None):
        return self.find_stream_by_language(self.audio, lang)
    
    def find_subtitle_by_language(self, lang=None):
        return self.find_stream_by_language(self.subtitle, lang)
            

class HandBrakeScanner(HandBrake):
    default_scanfile = "handbrake.scan"
    
    def __str__(self):
        lines = []
        too_short = 0
        for title in self.titles:
            if title.num_minutes() >= self.min_time:
                lines.append("mplayer dvd://%d/%s" % (title.title_num, self.source))
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
    
    def parseOptions(self, options):
        self.preferred_lang = options.lang
        self.min_time = options.min_time
        self.scanfile = options.scanfile
        if self.scanfile:
            if os.path.isdir(self.source):
                self.scanfile = os.path.join(self.source, self.default_scanfile)
            else:
                dirname, basename = os.path.split(self.source)
                self.scanfile = os.path.join(dirname, basename + self.default_scanfile)
    
    def run(self):
        if self.scanfile:
            if os.path.exists(self.scanfile):
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
        re_duration = re.compile("  \+ duration: (.+)")
        re_vts = re.compile("  \+ vts (\d+), ttn (\d+), (.+)")
        re_size = re.compile("  \+ size: (.+), pixel aspect: (.+), display aspect: ([\.\d]+), ([\.\d]+) fps")
        re_subtitle_type = re.compile("    \+ (\d+), (.+) \(iso639-2: ([a-z]+)\) (.+)")

        for line in output.splitlines():
            #dprint(line)
            match = re_scan_num_title.match(line)
            if match:
                self.num_titles = int(match.group(2))
                if self.verbose: print "matched! num titles=%d" % self.num_titles
                self.titles = [Title(i+1, self) for i in range(self.num_titles)]
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
    
    def get_title(self, title_num):
        return self.titles[title_num - 1]

class HandBrakeEncoder(HandBrake):
    def __init__(self, source, scan, output, dvd_title, audio, subtitles):
        HandBrake.__init__(self, source)
        self.title_num = dvd_title
        self.output = output
        self.options = []
        self.select_audio(scan.get_title(self.title_num), audio.get_title(self.title_num))
        self.select_subtitles(scan.get_title(self.title_num), subtitles.get_title(self.title_num))
        
    def __str__(self):
        return "dvd_title=%d output=%s options=%s" % (self.title_num, self.output, " ".join(self.options))
    
    def select_audio(self, title, track_titles):
        tracks = []
        names = []
        for track, name in track_titles.iter_tracks():
            tracks.append(track)
            if not name:
                audio = title.audio[track - 1]
                name = audio.lang
            names.append(name)
        
        if not tracks:
            default_set = title.find_audio_by_language()
            default = default_set[0]
            tracks.append(default.order)
            names.append(default.lang)
        
        self.options.extend(["-a", ",".join([str(t) for t in tracks]),
                             "-A", ",".join(names)])
    
    def select_subtitles(self, title, track_titles):
        tracks = []
        names = []
        scan = False
        for track, name in track_titles.iter_tracks():
            tracks.append(track)
            if not name:
                sub = title.subtitle[track - 1]
                name = sub.lang
            names.append(name)
        
        if not tracks:
            vobsub = None
            cc = None
            default_set = title.find_subtitle_by_language()
            for sub in default_set:
                if vobsub is None and sub.type == "vobsub":
                    vobsub = sub
                if cc is None and sub.type == "cc":
                    cc = sub
            if cc is not None:
                tracks.append(cc.order)
                names.append(cc.lang)
            if vobsub is not None:
                tracks.append(vobsub.order)
                names.append(vobsub.lang)
        
        for track in tracks:
            sub = title.subtitle[track - 1]
            if sub.type == "vobsub":
                scan = True
                tracks[0:0] = ["scan"]
                break
        
        self.options.extend(["-s", ",".join([str(t) for t in tracks])])
        if scan:
            self.options.extend(["-F", "1", "--subtitle-burn", "1"])
        

class TrackInfo(object):
    def __init__(self):
        self.order = list()
        self.info = dict()
    
    def add_track(self, index, name):
        self.order.append(index)
        self.info[index] = name
    
    def iter_tracks(self):
        for i in self.order:
            yield i, self.info[i]

class TrackOptions(object):
    def __init__(self, args):
        self.dvd_titles = dict()
        if args is not None:
            self.parse(args)
    
    def parse(self, args):
        print args
        i = 0
        while i + 1 < len(args):
            dvd_title = int(args[i])
            range = parseIntSet(args[i + 1])
            titles = []
            if i + 2 < len(args):
                arg = args[i + 2]
                vals = csv_split(arg)
                try:
                    test = int(vals[0])
                except:
                    titles = vals
            if titles:
                i += 3
            else:
                i += 2
                titles = []
            titles.extend([''] * len(range))
            track_titles = TrackInfo()
            for track_index, title in zip(range, titles):
                track_titles.add_track(track_index, title)
            self.dvd_titles[dvd_title] = track_titles
        print self.dvd_titles
    
    def get_title(self, title_num):
        try:
            return self.dvd_titles[title_num]
        except KeyError:
            return TrackInfo()


def parse_episodes(args):
    print args
    episodes = []
    episode = int(args[0])
    range = parseIntSet(args[1])
    titles = []
    if len(args) == 3:
        titles = csv_split(args[2])
    titles.extend([''] * len(range))
    for track_index, title in zip(range, titles):
        episodes.append((episode, track_index, title))
        episode += 1
    print episodes
    return episodes


if __name__ == "__main__":
    parser=argparse.ArgumentParser(description="Convert titles in a DVD image to Matroska files")
    parser.add_argument("--lang", action="store", default="eng",
                      help="Preferred language")
    parser.add_argument("--min-time", action="store", type=int, default=2,
                      help="Minimum time (minutes) for bonus feature to be valid")
    parser.add_argument("--crop", action="store", dest="crop", default="0:0:0:0", help="Crop parameters (default %(default)s)")
    parser.add_argument("--ext", action="store", dest="ext", default="mkv", help="Output file format (default %(default)s)")
    parser.add_argument("--scanfile", action="store_true", default=False, help="Store output of scan to increase speed on subsequent runs (default handbrake.scan)")
    parser.add_argument("-o", action="store", dest="output", default="", help="Output directory  (default current directory)")
    parser.add_argument("-i", action="store_true", dest="info", default=False, help="Only print info")
    parser.add_argument("-t", action="store", dest="title", default='', help="Movie or series title")
    parser.add_argument("-f", action="store", dest="film_series", default=[], nargs=2, metavar=("SERIES_NAME", "FILM_NUMBER"), help="Film series name and number in series (e.g. \"James Bond\" 1 or \"Harry Potter\" 8 etc.)")
    parser.add_argument("-s", action="store", type=int, dest="season", default=-1, help="Season number")
    parser.add_argument("-e", action="store", dest="episode", default=[], nargs="+", metavar=("NUMBER DVD_TITLE_RANGE", "NAME,NAME"), help="Starting episode number, comma/dash separated range of titles to use, and optional comma separated list of episode names")
    parser.add_argument("-x", action="store", dest="extra", default=[], nargs="+", metavar=("NUMBER DVD_TITLE_RANGE", "NAME,NAME"), help="Starting bonus feature number, comma/dash separated range of titles to use, and optional comma separated list of bonus feature names")
    parser.add_argument("-a", action="store", dest="audio", nargs="+", metavar="DVD_TITLE AUDIO_TRACK_NUMBER [TITLE,TITLE...]", help="DVD Title number, range of audio track numbers and optional corresponding titles")
    parser.add_argument("-c", action="store", dest="subtitles", nargs="+", metavar="DVD_TITLE SUBTITLE_TRACK_NUMBER [TITLE,TITLE...]", help="DVD Title number, range of subtitle caption numbers and optional corresponding titles")
    parser.add_argument("feature", action="store", nargs="+", metavar="path [dvd_title]", help="Path to DVD image and dvd title number if encoding main feature (or the word 'scan' to scan image)")
    options = parser.parse_args()

    if len(options.feature) > 1 and options.feature[1] == 'scan':
        arg = options.feature[0]
        h = HandBrakeScanner(arg, options=options)
        h.run()
        print h
    else:
        queue = []
        audio = TrackOptions(options.audio)
        subtitles = TrackOptions(options.subtitles)
        print options
        source = options.feature[0]
        
        scan = HandBrakeScanner(source, options=options)
        scan.run()

        if len(options.feature) > 1:
            if options.title:
                dvd_title = int(options.feature[1])
                filename = canonical_filename(options.title, options.film_series, options.season, None, None, None, options.ext)
                encoder = HandBrakeEncoder(source, scan, filename, dvd_title, audio, subtitles)
                print "Main feature: %s" % encoder
                queue.append(encoder)
            else:
                print "Expecting main feature"
        if len(options.episode) > 0:
            print "episode"
            bonus = parse_episodes(options.episode)
            for episode, dvd_title, name in bonus:
                filename = canonical_filename(options.title, options.film_series, options.season, "e", episode, name, options.ext)
                encoder = HandBrakeEncoder(source, scan, filename, dvd_title, audio, subtitles)
                print "Episode: %s" % encoder
                queue.append(encoder)
        if len(options.extra) > 0:
            print "bonus features"
            bonus = parse_episodes(options.extra)
            for episode, dvd_title, name in bonus:
                filename = canonical_filename(options.title, options.film_series, options.season, "x", episode, name, options.ext)
                encoder = HandBrakeEncoder(source, scan, filename, dvd_title, audio, subtitles)
                print "Bonus Feature: %s" % encoder
                queue.append(encoder)
        
        for enc in queue:
            print enc
            
