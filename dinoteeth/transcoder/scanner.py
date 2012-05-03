import os, re, time

from common import *

from ..utils import vprint

class HandBrakeScanner(HandBrake):
    default_scanfile = "handbrake.scan"
    
    def __str__(self):
        lines = []
        too_short = 0
        for title in self.titles:
            if title.num_minutes() >= self.min_time:
                size = [int(t) for t in title.size.split("x")]
                if title.autocrop != "0/0/0/0":
                    crop = [int(t) if int(t) > 2 else 0 for t in title.autocrop.split("/")]
                    vf = "-vf crop=%d:%d:%d:%d" % (size[0] - crop[2] - crop[3],
                                                   size[1] - crop[0] - crop[1],
                                                   crop[2], crop[0])
                else:
                    vf = ""
                lines.append("mplayer dvd://%d/%s %s" % (title.title_num, self.source, vf))
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
        self.titles = []
        
        parser = FullDvdBackupParser(output)
        parser.parse_into(self)
    
    def get_title(self, title_num):
        if title_num > len(self.titles):
            for i in range(len(self.titles), title_num):
                self.titles.append(Title(i+1, self))
            self.num_titles = len(self.titles)
        return self.titles[title_num - 1]


class FullDvdBackupParser(object):
    re_scan_num_title = re.compile("(\[.+\])? scan: DVD has (\d+) title")
    re_scan_title = re.compile("(\[.+\])? scan: scanning title (\d+)")
    re_audio = re.compile("(\[.+\])? scan: checking audio (\d+)")
    re_dvd_stream_id = re.compile("(\[.+\])? scan: id=(?:0x)?([0-9a-f]+)bd, lang=(.+), 3cc=([a-z]+)")
    re_mkv_input = re.compile("Input #(\d+)\, matroska.+")
    re_mkv_stream_id = re.compile(".+Stream #\d+\.(\d+)\((.+)\): ([a-zA-Z]+): .+")
    re_subtitle = re.compile("(\[.+\])? scan: checking subtitle (\d+)")
    re_preview = re.compile("(\[.+\])? scan: decoding previews for title (\d+)")
    re_preview_audio = re.compile("(\[.+\])? scan: audio 0x([0-9a-f]+): (.+), rate=(\d+)Hz, bitrate=(\d+) (.+)")
    re_title_summary = re.compile("\+ title (\d+):")
    re_autocrop = re.compile("  \+ autocrop: (.+)")
    re_duration = re.compile("  \+ duration: (.+)")
    re_vts = re.compile("  \+ vts (\d+), ttn (\d+), (.+)")
    re_size = re.compile("  \+ size: (.+), pixel aspect: (.+), display aspect: ([\.\d]+), ([\.\d]+) fps")
    re_subtitle_type = re.compile("    \+ (\d+), (.+) \(iso639-2: ([a-z]+)\) (.+)")

    def __init__(self, output):
        self.output = output

    def parse_into(self, scan):
        self.scan = scan
        
        current_title = None
        current_stream = None
        stream_flag = None
        
        mkv_counters = {'Input': 1, 'Video': 1, 'Audio': 1, 'Subtitle': 1}
        for line in self.output.splitlines():
            vprint(4, line)
            match = self.re_scan_num_title.match(line)
            if match:
                scan.num_titles = int(match.group(2))
                vprint(3, "matched! num titles=%d" % scan.num_titles)
                scan.titles = [Title(i+1, scan) for i in range(scan.num_titles)]
                continue
            match = self.re_preview.match(line)
            if match:
                title = int(match.group(2))
                vprint(3, "matched! preview: title=%d" % title)
                current_title = scan.get_title(title)
                current_stream = None
                continue
            match = self.re_scan_title.match(line)
            if match:
                title = int(match.group(2))
                vprint(3, "matched! title=%d" % title)
                current_title = scan.get_title(title)
                current_stream = None
                continue
            match = self.re_mkv_input.match(line)
            if match:
                input = int(match.group(1))
                vprint(3, "matched! mkv input=%d" % input)
                current_title = scan.get_title(mkv_counters['Input'])
                mkv_counters['Input'] += 1
                current_stream = None
                continue
            match = self.re_title_summary.match(line)
            if match:
                title = int(match.group(1))
                vprint(3, "matched! + title=%d" % title)
                current_title = scan.get_title(title)
                current_stream = None
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
                    match = self.re_subtitle_type.match(line)
                    if match:
                        order = int(match.group(1))
                        try:
                            subtitle = current_title.subtitle[order - 1]
                        except IndexError:
                            # closed captioned subtitles aren't listed in
                            # earlier subtitle scans, so add it here.
                            subtitle = Subtitle(order)
                            current_title.subtitle.append(subtitle)
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
            
            if current_title:
                if line.startswith("  + Main Feature"):
                    vprint(3, "Main feature!")
                    current_title.main_feature = True
                    continue
                match = self.re_autocrop.match(line)
                if match:
                    current_title.autocrop = match.group(1)
                    vprint(3, "autocrop = %s" % current_title.autocrop)
                    continue
                match = self.re_duration.match(line)
                if match:
                    current_title.duration = match.group(1)
                    vprint(3, "duration = %s" % current_title.duration)
                    continue
                match = self.re_vts.match(line)
                if match:
                    current_title.vts = int(match.group(1))
                    vprint(3, "vts = %d" % current_title.vts)
                    continue
                match = self.re_size.match(line)
                if match:
                    current_title.size = match.group(1)
                    current_title.pixel_aspect = match.group(2)
                    current_title.display_aspect = match.group(3)
                    current_title.fps = match.group(4)
                    vprint(3, "display aspect = %s" % current_title.display_aspect)
                    continue
                match = self.re_audio.match(line)
                if match:
                    order = int(match.group(2))
                    vprint(3, "matched! audio=%d" % order)
                    current_stream = Audio(order)
                    current_title.audio.append(current_stream)
                    continue
                match = self.re_preview_audio.match(line)
                if match:
                    hex_id = match.group(2)
                    if hex_id.endswith('bd'):
                        hex_id = hex_id[0:2]
                    id = int(hex_id, 16)
                    vprint(3, "matched! preview audio=%d" % id)
                    audio = current_title.find_audio_by_mplayer_id(id)
                    if audio is None:
                        order = len(current_title.audio) + 1
                        vprint(0, "failed matching audio stream %d.  HandBrake scan output probably changed. Assuming it is stream #%d" % (id, order))
                        audio = Audio(order)
                        current_title.audio.append(audio)
                        audio.mplayer_id = id
                    audio.rate = int(match.group(4))
                    audio.bitrate = int(match.group(5))
                    audio.codec = match.group(6)
                    continue
                match = self.re_subtitle.match(line)
                if match:
                    order = int(match.group(2))
                    vprint(3, "matched! subtitle=%d" % order)
                    current_stream = Subtitle(order)
                    current_title.subtitle.append(current_stream)
                    continue
                match = self.re_mkv_stream_id.match(line)
                if match:
                    id = int(match.group(1))
                    vprint(3, "matched mkv stream! mplayer_id=%d" % id)
                    stream_flag = match.group(3)
                    order = mkv_counters.get(stream_flag, 0)
                    if stream_flag == "Audio":
                        current_stream = Audio(order)
                        current_title.audio.append(current_stream)
                    elif stream_flag == "Subtitle":
                        current_stream = Subtitle(order)
                        current_title.subtitle.append(current_stream)
                    elif stream_flag == "Video":
                        continue
                    else:
                        vprint(0, "ignoring mkv stream type %s" % stream_flag)
                    mkv_counters[stream_flag] += 1
                    current_stream.mplayer_id = id
                    current_stream.lang = match.group(2)
                    if not current_stream.name:
                        current_stream.name = current_stream.lang
                    current_stream.threecc = match.group(2)
                    continue
            if current_stream:
                match = self.re_dvd_stream_id.match(line)
                if match:
                    id = int(match.group(2), 16)
                    vprint(3, "matched dvd stream! id=%d" % id)
                    current_stream.mplayer_id = id
                    current_stream.lang = match.group(3)
                    if not current_stream.name:
                        current_stream.name = current_stream.lang
                    current_stream.threecc = match.group(4)
                    continue
        
        self.cleanup_streams()
    
    def cleanup_streams(self):
        for title in self.scan.titles:
            title.cleanup_streams()
