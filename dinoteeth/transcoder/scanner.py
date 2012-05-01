import os, re, time

from common import *

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
        self.vprint(0, "-Running HandBrake --scan %s" % self.source)
        if self.scanfile:
            if os.path.exists(self.scanfile):
                self.vprint(0, "--Using previous scan %s" % self.scanfile)
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

        mkv_counters = {'Input': 1, 'Video': 1, 'Audio': 1, 'Subtitle': 1}
        for line in output.splitlines():
            self.vprint(4, line)
            match = re_scan_num_title.match(line)
            if match:
                self.num_titles = int(match.group(2))
                self.vprint(3, "matched! num titles=%d" % self.num_titles)
                self.titles = [Title(i+1, self) for i in range(self.num_titles)]
                continue
            match = re_preview.match(line)
            if match:
                title = int(match.group(2))
                self.vprint(3, "matched! preview: title=%d" % title)
                self.current_title = self.get_title(title)
                self.current_stream = None
                continue
            match = re_scan_title.match(line)
            if match:
                title = int(match.group(2))
                self.vprint(3, "matched! title=%d" % title)
                self.current_title = self.get_title(title)
                self.current_stream = None
                continue
            match = re_mkv_input.match(line)
            if match:
                input = int(match.group(1))
                self.vprint(3, "matched! mkv input=%d" % input)
                self.current_title = self.get_title(mkv_counters['Input'])
                mkv_counters['Input'] += 1
                self.current_stream = None
                continue
            match = re_title_summary.match(line)
            if match:
                title = int(match.group(1))
                self.vprint(3, "matched! + title=%d" % title)
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
                        self.vprint(2, subtitle)
            
            if self.current_title:
                if line.startswith("  + Main Feature"):
                    self.vprint(3, "Main feature!")
                    self.current_title.main_feature = True
                    continue
                match = re_autocrop.match(line)
                if match:
                    self.current_title.autocrop = match.group(1)
                    self.vprint(3, "autocrop = %s" % self.current_title.autocrop)
                    continue
                match = re_duration.match(line)
                if match:
                    self.current_title.duration = match.group(1)
                    self.vprint(3, "duration = %s" % self.current_title.duration)
                    continue
                match = re_vts.match(line)
                if match:
                    self.current_title.vts = int(match.group(1))
                    self.vprint(3, "vts = %d" % self.current_title.vts)
                    continue
                match = re_size.match(line)
                if match:
                    self.current_title.size = match.group(1)
                    self.current_title.pixel_aspect = match.group(2)
                    self.current_title.display_aspect = match.group(3)
                    self.current_title.fps = match.group(4)
                    self.vprint(3, "display aspect = %s" % self.current_title.display_aspect)
                    continue
                match = re_audio.match(line)
                if match:
                    order = int(match.group(2))
                    self.vprint(3, "matched! audio=%d" % order)
                    self.current_stream = Audio(order)
                    self.current_title.audio.append(self.current_stream)
                    continue
                match = re_preview_audio.match(line)
                if match:
                    hex_id = match.group(2)
                    if hex_id.endswith('bd'):
                        hex_id = hex_id[0:2]
                    id = int(hex_id, 16)
                    self.vprint(3, "matched! preview audio=%d" % id)
                    audio = self.current_title.find_audio_by_mplayer_id(id)
                    if audio is None:
                        order = len(self.current_title.audio) + 1
                        self.vprint(0, "failed matching audio stream %d.  HandBrake scan output probably changed. Assuming it is stream #%d" % (id, order))
                        audio = Audio(order)
                        self.current_title.audio.append(audio)
                        audio.mplayer_id = id
                    audio.rate = int(match.group(4))
                    audio.bitrate = int(match.group(5))
                    audio.codec = match.group(6)
                    continue
                match = re_subtitle.match(line)
                if match:
                    order = int(match.group(2))
                    self.vprint(3, "matched! subtitle=%d" % order)
                    self.current_stream = Subtitle(order)
                    self.current_title.subtitle.append(self.current_stream)
                    continue
                match = re_mkv_stream_id.match(line)
                if match:
                    id = int(match.group(1))
                    self.vprint(3, "matched mkv stream! mplayer_id=%d" % id)
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
                        self.vprint(0, "ignoring mkv stream type %s" % stream_flag)
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
                    self.vprint(3, "matched dvd stream! id=%d" % id)
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
