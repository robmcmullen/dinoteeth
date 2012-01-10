#!/usr/bin/env python
"""Rip DVDs and encode to mkv

Requires:

mplayer
normalize
mkvmerge
mkvextract
mkvpropedit
HandBrake CLI
"""

import os, sys, re, tempfile, time, copy
import subprocess as sub
from threading import Thread
from Queue import Queue, Empty
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..")) # to find third_party
try:
    import argparse
except:
    import third_party.argparse as argparse
from utils import encode_title_text, canonical_filename

# Global verbosity
VERBOSE = 0
LOGFILE = None
LOGLEVEL = 2

def vprint(verbosity_level, txt=""):
    global VERBOSE
    global LOGFILE
    if VERBOSE >= verbosity_level or LOGFILE is not None:
        if not isinstance(txt, basestring):
            txt = str(txt)
        if VERBOSE >= verbosity_level:
            print "%s" % txt.encode('utf-8')
        if LOGFILE is not None and LOGLEVEL >= verbosity_level:
            LOGFILE.write("%s\n" % txt)

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
        kwargs[key] = ",".join(current)

    def appendKeywordArgs(self, kwargs, key, *args):
        self.verifyKeywordExists(key, kwargs)
        current = kwargs[key]
        current.extend(*args)
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
    
    def get_command_line(self):
        args = [self.full_path_to_exe]
        args.extend(self.args)
        return args
    
    def popen(self):
        args = self.get_command_line()
        vprint(1, "popen: %s" % str(args))
        p = sub.Popen(args, stdout=sub.PIPE, stderr=sub.PIPE)
        return p
    
    def run(self):
        p = self.popen()
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
        vprint(2, output)
    
    def parseErrors(self, output):
        vprint(2, output)
        pass

class MkvScanner(ExeRunner):
    full_path_to_exe = "/usr/bin/mkvmerge"
    
    def __str__(self):
        return "\n".join("Track #%d: %s (%s)" % t for t in self.tracks)
    
    def setCommandLine(self, source, options=None, *args, **kwargs):
        self.args = ['--identify', source]
    
    def parseOutput(self, output):
        self.handbrake_to_mkv = dict()
        self.tracks = []

        handbrake_id = 1
        mkv_id = -1
        for line in output.splitlines():
            if "Track ID" in line:
                details = line.split()
                mkv_id = int(details[2][:-1])
                type = details[3]
                codec = details[4][1:-1]
                self.tracks.append((mkv_id, type, codec))
                if type == 'audio':
                    self.handbrake_to_mkv[handbrake_id] = mkv_id
                    handbrake_id += 1
    
    def get_mkv_id(self, handbrake_audio_id):
        return self.handbrake_to_mkv[handbrake_audio_id]

class MkvPropEdit(ExeRunner):
    full_path_to_exe = "/usr/bin/mkvpropedit"
    
    def setCommandLine(self, source, dvd_title=1, scan=None, mkv=None, encoder=None, options=None, *args, **kwargs):
        vprint(0, "-Using mkvpropedit to add names to tracks")
        self.args = [source]
        self.args.extend(["-e", "track:1", "-s", "name=%s" % options.name])
        title = scan.get_title(dvd_title)
        #print title
        audio_index = 0
        sub_index = 0
        for mkv_id, track_type, codec in mkv.tracks:
            if track_type == "audio":
                order = encoder.audio_track_order[audio_index]
                audio_index += 1
                #print "audio order: %d" % order
                stream = title.audio[order - 1]
                self.args.extend(["-e", "track:%d" % mkv_id, "-s", "name=%s" % stream.name])
            elif track_type == "subtitles":
                order = encoder.subtitle_track_order[sub_index]
                sub_index += 1
                #print "subtitle order: %d" % order
                stream = title.subtitle[order - 1]
                self.args.extend(["-e", "track:%d" % mkv_id, "-s", "name=%s" % stream.name])

class MkvAudioExtractor(ExeRunner):
    full_path_to_exe = "/usr/bin/mkvextract"
    
    def setCommandLine(self, source, mkv=None, options=None, *args, **kwargs):
        self.args = ["tracks", source]
        self.handbrake_to_mp3 = dict()
        for handbrake_id, mkv_id in mkv.handbrake_to_mkv.iteritems():
            output = "tmp.%s.%d.mp3" % (source, handbrake_id)
            self.args.append("%d:%s" % (mkv_id, output))
            self.handbrake_to_mp3[handbrake_id] = output

class MplayerAudioExtractor(ExeRunner):
    full_path_to_exe = "/usr/bin/mplayer"
    
    def setCommandLine(self, source, output="", aid=128, options=None, *args, **kwargs):
        self.args = ["-nocorrect-pts", "-quiet", "-vc", "null", "-vo", "null",
                     "-ao", "pcm:fast:file=%s" % output, "-aid", str(aid), source]

class VOBAudioExtractor(object):
    def __init__(self, source, title, track_order, output):
        self.handbrake_to_mp3 = dict()
        self.source = source
        self.title = title
        self.url = "dvd://%d//%s" % (title.title_num, source)
        self.track_order = track_order
        self.output = output
        
    def run(self):
        vprint(0, "-Using mplayer to rip audio tracks from %s" % self.url)
        handbrake_id = 0
        for order in self.track_order:
            handbrake_id += 1
            vprint(0, "--Ripping audio track %d" % order)
            stream = self.title.audio[order - 1]
            #print stream
            output = "tmp.%s.%d.wav" % (self.output, handbrake_id)
            self.handbrake_to_mp3[handbrake_id] = output
            wav = MplayerAudioExtractor(self.url, output=output, aid=stream.mplayer_id)
            wav.run()
    
    def cleanup(self):
        for h_id, filename in self.handbrake_to_mp3.iteritems():
            os.remove(filename)

class AudioGain(ExeRunner):
    full_path_to_exe = "/usr/bin/normalize"
    
    def setCommandLine(self, source, extractor=None, options=None, *args, **kwargs):
        self.extractor = extractor
        vprint(0, "-Using normalize to compute audio gain for %s" % source)
        self.args = ["-n", "--no-progress"]
        self.normalize_order = []
        for handbrake_id, output in extractor.handbrake_to_mp3.iteritems():
            self.args.append(output)
            self.normalize_order.append(handbrake_id)

    def parseOutput(self, output):
        self.gains = ['']*len(self.normalize_order)

        index = 0
        for line in output.splitlines():
            if 'dB' in line:
                details = line.split()
                gain = details[2][:-2]
                self.gains[self.normalize_order[index] - 1] = gain
                index += 1
        vprint(0, "--Computed gains: %s" % str(self.gains))
        self.extractor.cleanup()

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
        self.mplayer_id = -1
        self.lang = "unknown"
        self.threecc = "unk"
        self.name = ""

class Audio(Stream):
    def __init__(self, *args, **kwargs):
        Stream.__init__(self, *args, **kwargs)
        self.rate = -1
        self.bitrate = -1
        self.codec = ""
    
    def __str__(self):
        return "audio #%d: %s id=%d %s %s %dkHz %dkbps %s" % (self.order, self.name, self.mplayer_id, self.threecc, self.lang, self.rate/1000, self.bitrate/1000, self.codec)

class Subtitle(Stream):
    def __init__(self, *args, **kwargs):
        Stream.__init__(self, *args, **kwargs)
        self.type = "vobsub"
    
    def __str__(self):
        return "subtitle #%d: %s id=%d %s %s %s" % (self.order, self.name, self.mplayer_id, self.lang, self.threecc, self.type)

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
    
    def find_audio_by_mplayer_id(self, id):
        for audio in self.audio:
            if audio.mplayer_id == id:
                return audio
    
    def find_audio_by_handbrake_id(self, id):
        for audio in self.audio:
            if audio.order == id:
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
            
    def cleanup_streams(self):
        cleaned = []
        for audio in self.audio:
            if audio.mplayer_id == -1:
                vprint(1, "Found inactive audio %d" % audio.order)
            else:
                cleaned.append(audio)
        self.audio = cleaned
        cleaned = []
        for sub in self.subtitle:
            if sub.mplayer_id == -1:
                vprint(1, "Found inactive subtitle %d" % sub.order)
            else:
                cleaned.append(sub)
        self.subtitle = cleaned

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
        self.titles = []
        self.current_title = None
        self.current_stream = None
        stream_flag = None
        re_scan_num_title = re.compile("(\[.+\])? scan: DVD has (\d+) title")
        re_scan_title = re.compile("(\[.+\])? scan: scanning title (\d+)")
        re_audio = re.compile("(\[.+\])? scan: checking audio (\d+)")
        re_dvd_stream_id = re.compile("(\[.+\])? scan: id=0x([0-9a-f]+)bd, lang=(.+), 3cc=([a-z]+)")
        re_mkv_input = re.compile("Input #(\d+)\, matroska.+")
        re_mkv_stream_id = re.compile(".+Stream #\d+\.(\d+)\((.+)\): ([a-zA-Z]+): .+")
        re_subtitle = re.compile("(\[.+\])? scan: checking subtitle (\d+)")
        re_preview = re.compile("(\[.+\])? scan: decoding previews for title (\d+)")
        re_preview_audio = re.compile("(\[.+\])? scan: audio 0x([0-9a-f]+): (.+), rate=(\d+)Hz, bitrate=(\d+) (.+)")
        re_title_summary = re.compile("\+ title (\d+):")
        re_duration = re.compile("  \+ duration: (.+)")
        re_vts = re.compile("  \+ vts (\d+), ttn (\d+), (.+)")
        re_size = re.compile("  \+ size: (.+), pixel aspect: (.+), display aspect: ([\.\d]+), ([\.\d]+) fps")
        re_subtitle_type = re.compile("    \+ (\d+), (.+) \(iso639-2: ([a-z]+)\) (.+)")

        mkv_counters = {'Input': 1, 'Video': 1, 'Audio': 1, 'Subtitle': 1}
        for line in output.splitlines():
            vprint(4, line)
            match = re_scan_num_title.match(line)
            if match:
                self.num_titles = int(match.group(2))
                vprint(3, "matched! num titles=%d" % self.num_titles)
                self.titles = [Title(i+1, self) for i in range(self.num_titles)]
                continue
            match = re_preview.match(line)
            if match:
                title = int(match.group(2))
                vprint(3, "matched! preview: title=%d" % title)
                self.current_title = self.get_title(title)
                self.current_stream = None
                continue
            match = re_scan_title.match(line)
            if match:
                title = int(match.group(2))
                vprint(3, "matched! title=%d" % title)
                self.current_title = self.get_title(title)
                self.current_stream = None
                continue
            match = re_mkv_input.match(line)
            if match:
                input = int(match.group(1))
                vprint(3, "matched! mkv input=%d" % input)
                self.current_title = self.get_title(mkv_counters['Input'])
                mkv_counters['Input'] += 1
                self.current_stream = None
                continue
            match = re_title_summary.match(line)
            if match:
                title = int(match.group(1))
                vprint(3, "matched! + title=%d" % title)
                self.current_title = self.get_title(title)
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
                        subtitle.threecc = match.group(3)
                        type = match.group(4).lower()
                        if "vobsub" in type:
                            subtitle.type = "vobsub"
                            subtitle.name = "Subtitles"
                        elif "cc" in type and "text" in type:
                            subtitle.type = "cc"
                            subtitle.name = "Closed Captions"
                        else:
                            subtitle.type = "unknown"
                        vprint(2, subtitle)
            
            if self.current_title:
                if line.startswith("  + Main Feature"):
                    vprint(3, "Main feature!")
                    self.current_title.main_feature = True
                    continue
                match = re_duration.match(line)
                if match:
                    self.current_title.duration = match.group(1)
                    vprint(3, "duration = %s" % self.current_title.duration)
                    continue
                match = re_vts.match(line)
                if match:
                    self.current_title.vts = int(match.group(1))
                    vprint(3, "vts = %d" % self.current_title.vts)
                    continue
                match = re_size.match(line)
                if match:
                    self.current_title.size = match.group(1)
                    self.current_title.pixel_aspect = match.group(2)
                    self.current_title.display_aspect = match.group(3)
                    self.current_title.fps = match.group(4)
                    vprint(3, "display aspect = %s" % self.current_title.display_aspect)
                    continue
                match = re_audio.match(line)
                if match:
                    order = int(match.group(2))
                    vprint(3, "matched! audio=%d" % order)
                    self.current_stream = Audio(order)
                    self.current_title.audio.append(self.current_stream)
                    continue
                match = re_preview_audio.match(line)
                if match:
                    hex_id = match.group(2)
                    if hex_id.endswith('bd'):
                        hex_id = hex_id[0:2]
                    id = int(hex_id, 16)
                    vprint(3, "matched! preview audio=%d" % id)
                    audio = self.current_title.find_audio_by_mplayer_id(id)
                    audio.rate = int(match.group(4))
                    audio.bitrate = int(match.group(5))
                    audio.codec = match.group(6)
                    continue
                match = re_subtitle.match(line)
                if match:
                    order = int(match.group(2))
                    vprint(3, "matched! subtitle=%d" % order)
                    self.current_stream = Subtitle(order)
                    self.current_title.subtitle.append(self.current_stream)
                    continue
                match = re_mkv_stream_id.match(line)
                if match:
                    id = int(match.group(1))
                    vprint(3, "matched mkv stream! mplayer_id=%d" % id)
                    stream_flag = match.group(3)
                    order = mkv_counters.get(stream_flag, 0)
                    if stream_flag == "Audio":
                        self.current_stream = Audio(order)
                        self.current_title.audio.append(self.current_stream)
                    elif stream_flag == "Subtitle":
                        self.current_stream = Subtitle(order)
                        self.current_title.subtitle.append(self.current_stream)
                    elif stream_flag == "Video":
                        continue
                    else:
                        vprint(0, "ignoring mkv stream type %s" % stream_flag)
                    mkv_counters[stream_flag] += 1
                    self.current_stream.mplayer_id = id
                    self.current_stream.lang = match.group(2)
                    if not self.current_stream.name:
                        self.current_stream.name = self.current_stream.lang
                    self.current_stream.threecc = match.group(2)
                    continue
            if self.current_stream:
                match = re_dvd_stream_id.match(line)
                if match:
                    id = int(match.group(2), 16)
                    vprint(3, "matched dvd stream! id=%d" % id)
                    self.current_stream.mplayer_id = id
                    self.current_stream.lang = match.group(3)
                    if not self.current_stream.name:
                        self.current_stream.name = self.current_stream.lang
                    self.current_stream.threecc = match.group(4)
                    continue
        
        self.cleanup_streams()
    
    def cleanup_streams(self):
        for title in self.titles:
            title.cleanup_streams()
    
    def get_title(self, title_num):
        if title_num > len(self.titles):
            for i in range(len(self.titles), title_num):
                self.titles.append(Title(i+1, self))
            self.num_titles = len(self.titles)
        return self.titles[title_num - 1]

class HandBrakeEncoder(HandBrake):
    def __init__(self, source, scan, output, dvd_title, audio_spec, subtitle_spec, options, audio_only=False):
        HandBrake.__init__(self, source)
        self.source = source
        self.scan = scan
        self.title_num = dvd_title
        self.output = output
        self.title = scan.get_title(self.title_num)
        self.options = options
        self.audio_only = audio_only
        self.select_audio(audio_spec)
        self.select_subtitles(subtitle_spec)
        self.add_options(options)
        self.args.extend(["-o", output])
    
    def clone_audio_only(self):
        hb = HandBrakeEncoder(self.source, self.scan, self.output, self.title_num,
                              options, audio_only=True)
        return hb
        
    def __str__(self):
        return "%s output=%s options=%s" % (self.title, self.output, " ".join(self.args))
    
    def select_audio(self, track_titles):
        tracks = []
        names = []
        for track, name in track_titles.iter_tracks():
            tracks.append(track)
            audio = self.title.find_audio_by_handbrake_id(track)
            if name:
                # Override stream name to user's name
                audio.name = name
            else:
                name = audio.name
            names.append(name)
        
        if not tracks:
            default_set = self.title.find_audio_by_language()
            default = default_set[0]
            tracks.append(default.order)
            names.append(default.lang)
        
        self.audio_track_order = tracks
        
        self.args.extend(["-a", ",".join([str(t) for t in tracks]),
                             "-A", ",".join(names)])
    
    def select_subtitles(self, track_titles):
        tracks = []
        names = []
        scan = False
        for track, name in track_titles.iter_tracks():
            tracks.append(track)
            sub = self.title.subtitle[track - 1]
            if name:
                # Override stream name to user's name
                sub.name = name
            else:
                name = sub.name
            names.append(name)
        
        if not tracks:
            vobsub = None
            cc = None
            default_set = self.title.find_subtitle_by_language()
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
        
        self.subtitle_track_order = tracks[:]

        for track in tracks:
            sub = self.title.subtitle[track - 1]
            if sub.type == "vobsub":
                scan = True
                tracks[0:0] = ["scan"]
                break
        
        self.args.extend(["-s", ",".join([str(t) for t in tracks])])
        if scan:
            self.args.extend(["-F", "1", "--subtitle-burn", "1"])
    
    def add_options(self, options):
        self.args.extend(["-t", str(self.title.title_num)])
        if options.preview > 0:
            self.args.extend(["-c", "1-%d" % options.preview])
        if options.fast or self.audio_only:
            self.args.extend(["-r", "5"])
            self.args.extend(["-b", "100"])
            self.args.extend(["-w", "160"])
        else:
            self.args.extend(["-2", "-T", "--detelecine"])
            if options.deint:
                self.args.append("--decomb")
            self.args.extend(("-e", options.video_encoder))
            if options.x264_preset:
                self.args.extend(("--x264-preset", options.x264_preset))
            if options.x264_tune:
                self.args.extend(("--x264-tune", options.x264_tune))
            self.args.extend(("-b", str(options.video_bitrate)))
        if options.grayscale:
            self.args.append("-g")
        self.args.append("--loose-anamorphic")
        if self.title.display_aspect in ["16x9", "1.78", "1.77"]:
            self.args.extend(("--display-width", "854"))
        elif self.title.display_aspect in ["4x3", "1.33"]:
            self.args.extend(("--pixel-aspect", "8:9"))
        else:
            raise RuntimeError("Unknown aspect ratio %s" % self.title.display_aspect)
        self.args.extend(["--crop", options.crop])
        
        # Audio settings
        if options.fast:
            self.args.extend(("-E", "lame"))
            self.args.extend(("-B", "128"))
        else:
            self.args.extend(("-E", options.audio_encoder))
            self.args.extend(("-B", str(options.audio_bitrate)))
            if options.gain != 0.0:
                self.args.extend(("--gain", str(options.gain)))
    
    def enqueue_output(self, out, queue):
        for line in iter(out.readline, ''):
            queue.put(line)
        out.close()
    
    def run(self):
        if not self.audio_only and self.options.normalize:
            self.compute_gains()
        vprint(0, "-Using HandBrake to encode video %s" % self.output)
        p = self.popen()
        q_stderr = Queue()
        t_stderr = Thread(target=self.enqueue_output, args=(p.stderr, q_stderr))
        t_stderr.start()
        q_stdout = Queue()
        t_stdout = Thread(target=self.enqueue_output, args=(p.stdout, q_stdout))
        t_stdout.start()
        out = HandBrakeOutput()
        error = None
        while p.poll() is None and error is None:
            try:
                while True:
                    line = q_stdout.get_nowait()
                    vprint(2, "stdout-->%s<--" % line.rstrip())
            except Empty:
                vprint(3, "stdout empty")
            try:
                while True and error is None:
                    line = q_stderr.get_nowait()
                    error = out.process(line)
                    vprint(2, "-->%s<--" % line.rstrip())
                    if not line:
                        break
            except Empty:
                vprint(3, "stderr empty")
            time.sleep(1)
            vprint(3, "Poll: %s" % str(p.poll()))
        if error is not None:
            vprint(0, "-HandBrake encoding failed.")
            p.terminate()
        vprint(3, "Waiting for process to finish...")
        p.wait()
        vprint(3, "Waiting for thread join...")
        t_stderr.join()
        t_stdout.join()
        if error is None:
            vprint(0, "-HandBrake finished encoding %s" % self.output)
            if not self.audio_only:
                self.rename_tracks()
    
    def compute_gains_handbrake(self):
        fast = self.clone_audio_only()
        fast.run()
        mkv = MkvScanner(self.output)
        mkv.run()
        extractor = MkvAudioExtractor(self.output, mkv=mkv)
        extractor.run()
        normalizer = AudioGain(self.output, extractor=extractor)
        normalizer.run()
        try:
            index = self.args.index("--gain")
            index += 1
        except ValueError:
            index = len(self.args)
            self.args[index:index] = ["--gain"]
            index += 1
        self.args[index:index] = [",".join(normalizer.gains)]
    
    def compute_gains(self):
        vprint(0, "-Preparing to compute audio gain factors")
        extractor = VOBAudioExtractor(self.source, self.title, self.audio_track_order, self.output)
        extractor.run()
        normalizer = AudioGain(self.output, extractor=extractor)
        normalizer.run()
        try:
            index = self.args.index("--gain")
            index += 1
        except ValueError:
            index = len(self.args)
            self.args[index:index] = ["--gain"]
            index += 1
        self.args[index:index] = [",".join(normalizer.gains)]
    
    def rename_tracks(self):
        vprint(0, "-Preparing to rename tracks in %s" % self.output)
        mkv = MkvScanner(self.output)
        mkv.run()
        prop = MkvPropEdit(self.output, options=self.options, dvd_title=self.title_num, scan=self.scan, mkv=mkv, encoder=self)
        prop.run()

class HandBrakeOutput(object):
    """State machine to process only interesting bits of the HandBrake output
    
    """
    def __init__(self):
        self.expected_jobs = 0
        self.job = 0
        self.state = None
        self.configuration = ""
    
    def process(self, line):
        line = line.rstrip()
        if self.expected_jobs == 0:
            if "job(s) to process" in line:
                details = line.split(" ")
                self.expected_jobs = int(details[1])
            return
        if line.startswith("["):
            time, line = line.split("] ", 1)
        else:
            time = None
        if line == "starting job":
            self.job += 1
            return
        if line.startswith("x264 [error]"):
            _, error = line.split(": ", 1)
            vprint(0, "** x264 encoding error: %s" % error)
            if "stats file could not be written to" in error:
                vprint(0, "*** Likely out of space in temporary directory.  Try --tmp option.")
            return error
        if self.job > 0:
            if self.state == None:
                if line == "job configuration:":
                    self.state = line
                    return
                if line.startswith("Subtitle stream"):
                    info_unsplit, hits = line.split(": ", 1)
                    info = info_unsplit.split()
                    stream_id = info[2]
                    details = hits.split()
                    hits = int(details[0])
                    forced = int(details[2][1:])
                    if forced > 0:
                        vprint(0, "--burning in %d forced subtitles (of %d) for subtitle stream %s" % (forced, hits, stream_id))
                    else:
                        vprint(0, "--no forced subtitles to burn in for subtitle stream %s" % stream_id)
                if line.startswith("libhb: work result"):
                    _, ret = line.split(" = ", 1)
                    if ret == "0":
                        vprint(0, "-HandBrake finished successfully")
                    else:
                        vprint(0, "-Handbrake failed with return code %s" % ret)
                    return
            if self.state == "job configuration:":
                if time is not None:
                    self.configuration += line + "\n"
                else:
                    if self.job == self.expected_jobs:
                        vprint(0, "--starting final encode pass %s/%s" % (self.job, self.expected_jobs))
                        print self.configuration
                    else:
                        vprint(0, "--starting encode pass %s/%s" % (self.job, self.expected_jobs))
                        self.configuration = ""
                    self.state = None
                return
            if line.startswith("reader: done"):
                vprint(0, "--finished encode pass %s/%s" % (self.job, self.expected_jobs))
                self.state = None
                return


class TrackInfo(object):
    def __init__(self):
        self.order = list()
        self.name = dict()
    
    def __str__(self):
        return str(self.name)
    
    def add_track(self, index, name):
        self.order.append(index)
        self.name[index] = name
    
    def iter_tracks(self):
        for i in self.order:
            yield i, self.name[i]

def parse_episode_info(starting, dvd_titles, spec):
    # set defaults
    numbers = range(starting, starting + len(dvd_titles))
    names = [""] * len(dvd_titles)
    
    def parse_episode_numbers(number_spec):
        tokens = csv_split(number_spec)
        tokens = [int(t) for t in tokens]
        # Throw away any extra specified items in the list beyond the number of
        # expected dvd titles
        if len(tokens) > len(dvd_titles):
            tokens = tokens[0:len(dvd_titles)]
        elif len(tokens) > 0:
            num = tokens[-1] + 1
            for i in range(len(tokens), len(dvd_titles)):
                numbers[i] = num
                num += 1
        else:
            return
        numbers[0:len(tokens)] = tokens
    
    def parse_episode_names(number_spec):
        tokens = csv_split(number_spec)
        if len(tokens) > len(dvd_titles):
            tokens = tokens[0:len(dvd_titles)]
        names[0:len(tokens)] = tokens

    if len(spec) == 0:
        pass
    elif len(spec) == 1:
        try:
            parse_episode_numbers(spec[0])
        except ValueError:
            parse_episode_names(spec[0])
    elif len(spec) == 2:
        parse_episode_numbers(spec[0])
        parse_episode_names(spec[1])
    else:
        raise RuntimeError("Incorrect format specification")
    return numbers, names

def parse_stream_names(spec):
    info = TrackInfo()
    if spec:
        tracks = parseIntSet(spec[0])
        names = [''] * len(tracks)
        if len(spec) > 1:
            tokens = csv_split(spec[1])
            names[0:len(tokens)] = tokens
        for t, n in zip(tracks, names):
            info.add_track(t, n)
    return info

if __name__ == "__main__":
    global_parser = argparse.ArgumentParser(description="Convert titles in a DVD image to Matroska files")
    global_parser.add_argument("-v", "--verbose", default=0, action="count")
    global_parser.add_argument("--dry-run", action="store_true", default=False, help="Don't encode, just show what would have been encoded")
    global_parser.add_argument("--min-time", action="store", type=int, default=2,
                      help="Minimum time (minutes) for bonus feature to be valid")
    global_parser.add_argument("--scanfile", action="store_true", default=True, help="Store output of scan to increase speed on subsequent runs (default handbrake.scan)")
    global_parser.add_argument("--no-scanfile", action="store_true", dest="scanfile", default=True, help="No not store output of scan to increase speed on subsequent runs (default handbrake.scan)")
    global_parser.add_argument("--log", action="store_true", default=True, help="Store output of scan to increase speed on subsequent runs (default handbrake.log)")
    global_parser.add_argument("--tmp", action="store", default="", help="Directory for temporary files created during encoding process")
    global_parser.add_argument("-o", action="store", dest="output", default="", help="Output directory  (default current directory)")
    global_parser.add_argument("--info", action="store_true", dest="info", default=False, help="Only print info")
    global_parser.add_argument("-n", action="store", dest="name", default='', help="Movie or TV Series name")
    global_parser.add_argument("-f", action="store", dest="film_series", default=[], nargs=2, metavar=("SERIES_NAME", "FILM_NUMBER"), help="Film series name and number in series (e.g. \"James Bond\" 1 or \"Harry Potter\" 8 etc.)")
    global_parser.add_argument("-s", action="store", type=int, dest="season", default=-1, help="Season number")
    global_parser.add_argument("--lang", action="store", default="eng",
                      help="Preferred language")
    global_parser.add_argument("-i", action="store", dest="input", help="Path to DVD image")

    # Testing options not used for normal encoding tasks
    global_parser.add_argument("--mkv", action="store", help="Display audio information of specified .mkv file")
    global_parser.add_argument("--mkv-names", action="store", metavar=("MKV_FILE", "DVD_TITLE"), nargs=2, help="Rename tracks in .mkv file")


    sticky_parser = argparse.ArgumentParser(description="Sticky arguments that remain set until explicitly reset")
    sticky_parser.add_argument("--ext", action="store", dest="ext", default="mkv", help="Output file format (default %(default)s)")
    
    # Video options
    sticky_parser.add_argument("-b", "--vb", action="store", dest="video_bitrate", type=int, default=2000, help="Video bitrate (kb/s)")
    sticky_parser.add_argument("-g", "--grayscale", action="store_true", default=False, help="Grayscale encoding")
    sticky_parser.add_argument("--crop", action="store", dest="crop", default="0:0:0:0", help="Crop parameters (default %(default)s)")
    sticky_parser.add_argument("--deint", action="store_true", default=False, help="Add deinterlace (decomb) filter (slows processing by up to 50%)")
    sticky_parser.add_argument("--video-encoder", action="store", default="x264", help="Video encoder (default %(default)s)")
    sticky_parser.add_argument("--x264-preset", action="store", default="", help="x264 encoder preset")
    sticky_parser.add_argument("--x264-tune", action="store", default="film", help="x264 encoder tuning (typically either 'film' or 'animation')")
    
    # Audio options
    sticky_parser.add_argument("--audio-encoder", action="store", default="faac", help="Audio encoder (default %(default)s)")
    sticky_parser.add_argument("-B", "--ab", action="store", dest="audio_bitrate", type=int, default=160, help="Audio bitrate (kb/s)")
    sticky_parser.add_argument("--normalize", action="store_true", default=True, help="Automatically select gain values to normalize audio (uses an extra encoding pass)")
    sticky_parser.add_argument("--no-normalize", dest="normalize", action="store_false", default=True, help="Automatically select gain values to normalize audio (uses an extra encoding pass)")
    sticky_parser.add_argument("--gain", action="store", type=float, default=0.0, help="Specify audio gain (dB, positive values amplify)")

    # Testing options not used for normal encoding tasks
    sticky_parser.add_argument("--fast", action="store_true", default=False, help="Fast encoding mode to small video at constant 5fps")
    sticky_parser.add_argument("--preview", action="store", type=int, default=0, help="Preview the first PREVIEW chapters")


    title_parser = argparse.ArgumentParser(description="DVD Title options")
    title_parser.add_argument("-t", action="store", dest="dvd_title", default="", help="DVD title number (or list or range) to process")
    title_parser.add_argument("-e", action="store", dest="episode", default=None, nargs="*", metavar=("NUMBER", "NAME,NAME"), help="Optional starting episode number and optional comma separated list of episode names")
    title_parser.add_argument("-x", action="store", dest="bonus", default=None, nargs="*", metavar=("NUMBER", "NAME,NAME"), help="Optional starting bonus feature number and optional comma separated list of bonus feature names")
    title_parser.add_argument("-a", action="store", dest="audio", default=None, nargs="+", metavar="AUDIO_TRACK_NUMBER(s) [TITLE,TITLE...]", help="Range of audio track numbers and optional audio track names.  Note: if multiple DVD titles are specified in this title block, the audio tracks will apply to ALL of them")
    title_parser.add_argument("-c", action="store", dest="subtitles", default=None, nargs="+", metavar="SUBTITLE_TRACK_NUMBER(s) [TITLE,TITLE...]", help="Range of subtitle caption numbers and optional corresponding subtitle track names.  Note: if multiple DVD titles are specified in this title block, the audio tracks will apply to ALL of them")
    
    # Split argument list by the "-t" option so that each "-t" can have its
    # own arguments
    arg_sets = []
    start = 1
    while start < len(sys.argv):
        try:
            end = sys.argv.index("-t", start + 1)
            arg_set = sys.argv[start:end]
            arg_sets.append(arg_set)
            start = end
        except ValueError:
            arg_sets.append(sys.argv[start:])
            break
    global_args = arg_sets[0]
    title_args = arg_sets[1:]
    
    global_options, sticky_args = global_parser.parse_known_args(global_args)
    VERBOSE = global_options.verbose
    sticky_options = copy.copy(global_options)
    sticky_options, extra_args = sticky_parser.parse_known_args(sticky_args, sticky_options)
    title_options = []
    for args in title_args:
        sticky_options, extra_args = sticky_parser.parse_known_args(args, sticky_options)
        options = copy.copy(sticky_options)
        options, extra_args = title_parser.parse_known_args(extra_args, options)
        vprint(2, "title(s): %s" % options.dvd_title)
        if extra_args:
            global_options, ignored_args = global_parser.parse_known_args(extra_args, global_options)
        vprint(2, "global: %s" % global_options)
        vprint(2, "sticky: %s" % sticky_options)
        vprint(2, "options: %s" % options)
        title_options.append(options)
    
    VERBOSE = global_options.verbose
    
    queue = []
    vprint(2, global_options)
    source = global_options.input
    if not source:
        global_parser.print_usage()
        global_parser.exit()
    
    if global_options.log:
        LOGFILE = open(os.path.join(source, "handbrake.log"), "w")
    
    if global_options.tmp:
        os.environ["TEMP"] = global_options.tmp
    
    scan = HandBrakeScanner(source, options=global_options)
    scan.run()
    
    if global_options.mkv:
        mkv = MkvScanner(global_options.mkv)
        mkv.run()
        print scan.handbrake_to_mkv
        extractor = MkvAudioExtractor(global_options.mkv, mkv=mkv)
        extractor.run()
        normalizer = AudioGain(global_options.mkv, extractor=extractor)
        normalizer.run()
        sys.exit()
    if global_options.mkv_names:
        print scan
        filename = global_options.mkv_names[0]
        dvd_title = int(global_options.mkv_names[1])
        mkv = MkvScanner(filename)
        mkv.run()
        print mkv
        encoder = HandBrakeEncoder(source, scan, filename, dvd_title, global_options)
        prop = MkvPropEdit(filename, options=options, dvd_title=dvd_title, scan=scan, mkv=mkv, encoder=encoder)
        prop.run()
        sys.exit()

    if len(title_options) > 0:
        episode_number = 1
        bonus_number = 1
        for options in title_options:
            dvd_title_spec = options.dvd_title
            if not dvd_title_spec:
                title_parser.error("DVD title number must be specified.") 
            dvd_titles = parseIntSet(dvd_title_spec)
            
            audio = parse_stream_names(options.audio)
            subtitles = parse_stream_names(options.subtitles)
            
            if options.episode is not None:
                numbers, names = parse_episode_info(episode_number, dvd_titles, options.episode)
                
                # add each episode to queue
                for dvd_title, episode, name in zip(dvd_titles, numbers, names):
                    filename = canonical_filename(options.name, options.film_series, options.season, "e", episode, name, options.ext)
                    encoder = HandBrakeEncoder(source, scan, filename, dvd_title, audio, subtitles, options)
                    queue.append(encoder)
                
                # set up next default episode number
                episode_number = numbers[-1] + 1
            
            elif options.bonus is not None:
                numbers, names = parse_episode_info(bonus_number, dvd_titles, options.bonus)
                
                # add each bonus feature to queue
                for dvd_title, episode, name in zip(dvd_titles, numbers, names):
                    filename = canonical_filename(options.name, options.film_series, options.season, "x", episode, name, options.ext)
                    encoder = HandBrakeEncoder(source, scan, filename, dvd_title, audio, subtitles, options)
                    queue.append(encoder)
                
                # set up next default episode number
                bonus_number = numbers[-1] + 1
            
            else:
                dvd_title = dvd_titles[0]
                filename = canonical_filename(options.name, options.film_series, options.season, None, None, None, options.ext)
                encoder = HandBrakeEncoder(source, scan, filename, dvd_title, audio, subtitles, options)
                queue.append(encoder)

        for enc in queue:
            if global_options.dry_run:
                vprint(0, " ".join(enc.get_command_line()))
            else:
                enc.run()
        
    if global_options.log:
        LOGFILE.close()
