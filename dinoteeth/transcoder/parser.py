import os, re, time

from common import *

from ..utils import vprint


class HandBrakeScanParser(object):
    registered = []
    
    re_progress = re.compile("Scanning title.+ %")
    re_title_summary = re.compile("\+ title (\d+):")
    re_autocrop = re.compile("  \+ autocrop: (.+)")
    re_duration = re.compile("  \+ duration: (.+)")
    re_size = re.compile("  \+ size: (.+), pixel aspect: (.+), display aspect: ([\.\d]+), ([\.\d]+) fps")
    re_preview = re.compile("(\[.+\])? scan: decoding previews for title (\d+)")
    re_scan_title = re.compile("(\[.+\])? scan: scanning title (\d+)")
    re_audio_type = re.compile("    \+ (\d+), (.+) \(iso639-2: ([a-z]+)\), (.+)Hz, (.+)bps")
    re_subtitle_type = re.compile("    \+ (\d+), (.+) \(iso639-2: ([a-z]+)\) (.+)")
    
    @classmethod
    def register(cls, parser):
        cls.registered.append(parser)
    
    @classmethod
    def identify(cls, output):
        for parser in cls.registered:
            if parser.works_with(output):
                return parser(output)
        raise RuntimeError("No parser for this type of scan!")
    
    def __init__(self, output):
        self.output = output
    
    def parse_into(self, scan):
        self.parse_init()
        
        self.scan = scan
        
        self.current_title = None
        self.current_stream = None
        self.stream_flag = None
        for line in self.output.splitlines():
            line = self.re_progress.sub("", line)
            vprint(4, line)
            if self.process_line(line):
                continue
            
            if self.current_title:
                if self.process_title(line):
                    continue
            
            if self.current_stream:
                if self.process_stream(line):
                    continue
        
        self.cleanup_streams()
    
    def parse_init(self):
        pass
    
    def cleanup_streams(self):
        for title in self.scan.iter_titles():
            title.cleanup_streams()
    
    def get_interesting_name(self, text):
        items = text.split("(")
        best = items[0]
        for item in items[1:]:
            if "commentary" in item.lower():
                best = item
        best = best.strip(" )")
        return best
    
    def process_scan(self, line):
        if self.process_scan_common(line):
            return True
        if self.process_scan_subclass(line):
            return True
        return False
    
    def process_scan_common(self, line):
        match = self.re_preview.match(line)
        if match:
            title = int(match.group(2))
            vprint(3, "matched! preview: title=%d" % title)
            self.current_title = self.scan.get_title(title)
            self.current_stream = None
            self.process_title_init(line)
            return True
        match = self.re_scan_title.match(line)
        if match:
            title = int(match.group(2))
            vprint(3, "matched! title=%d" % title)
            self.current_title = self.scan.get_title(title)
            self.current_stream = None
            self.process_title_init(line)
            return True
    
    def process_scan_subclass(self, line):
        return False
    
    def process_line(self, line):
        if self.process_line_common(line):
            return True
        if self.process_line_subclass(line):
            return True
        return False
    
    def process_line_common(self, line):
        match = self.re_preview.match(line)
        if match:
            title = int(match.group(2))
            vprint(3, "matched! preview: title=%d" % title)
            self.current_title = self.scan.get_title(title)
            self.current_stream = None
            self.process_title_init(line)
            return True
        match = self.re_scan_title.match(line)
        if match:
            title = int(match.group(2))
            vprint(3, "matched! title=%d" % title)
            self.current_title = self.scan.get_title(title)
            self.current_stream = None
            self.process_title_init(line)
            return True
        match = self.re_title_summary.match(line)
        if match:
            title = int(match.group(1))
            vprint(3, "matched! + title=%d" % title)
            self.current_title = self.scan.get_title(title)
            self.current_stream = None
            self.stream_flag = ""
            return True
        if line.startswith("  + audio tracks"):
            self.stream_flag = "audio"
            return True
        if line.startswith("  + subtitle tracks"):
            self.stream_flag = "subtitle"
            return True
        if line.startswith("    +"):
            if self.stream_flag == "audio":
                match = self.re_audio_type.match(line)
                if match:
                    vprint(3, "current title:\n%s" % str(self.current_title))
                    vprint(3, "current title's audio:\n%s" % str(self.current_title.audio))
                    order = int(match.group(1))
                    vprint(2, "audio order: %d" % order)
                    try:
                        audio = self.current_title.audio[order - 1]
                    except IndexError:
                        audio = Audio(order)
                        audio.mplayer_id = order - 1
                        self.current_title.audio.append(audio)
                        vprint(1, "Adding audio %d to %s" % (order, self.current_title))
                    audio.threecc = match.group(3)
                    if audio.lang == "unknown":
                        audio.lang = match.group(3)
                    rate = int(match.group(4))
                    vprint(2, "audio sample rate: %s" % rate)
                    audio.rate = rate
                    rate = int(match.group(5))
                    vprint(2, "audio bitrate: %s" % rate)
                    audio.bitrate = rate
                    audio.name = self.get_interesting_name(match.group(2))
                    vprint(2, audio)
                    return True
            if self.stream_flag == "subtitle":
                match = self.re_subtitle_type.match(line)
                if match:
                    order = int(match.group(1))
                    vprint(2, "subtitle order: %d" % order)
                    try:
                        subtitle = self.current_title.subtitle[order - 1]
                    except IndexError:
                        # closed captioned subtitles aren't listed in
                        # earlier subtitle scans, so add it here.
                        subtitle = Subtitle(order)
                        subtitle.mplayer_id = order - 1
                        self.current_title.subtitle.append(subtitle)
                    subtitle.threecc = match.group(3)
                    if subtitle.lang == "unknown":
                        subtitle.lang = match.group(3)
                    type = match.group(4).lower()
                    if "vobsub" in type:
                        subtitle.type = "vobsub"
                        subtitle.name = "Subtitles"
                    elif "cc" in type and "text" in type:
                        subtitle.type = "cc"
                        subtitle.name = "Closed Captions"
                    elif "pgs" in type:
                        subtitle.type = "pgs"
                        subtitle.name = "Subtitles"
                    else:
                        subtitle.type = "unknown"
                    vprint(2, subtitle)
        return False
    
    def process_line_subclass(self, line):
        return False
    
    def process_title_init(self, line):
        pass

    def process_title(self, line):
        if self.process_title_common(line):
            return True
        if self.process_title_audio(line):
            return True
        if self.process_title_subtitle(line):
            return True
        if self.process_title_subclass(line):
            return True
        return False
    
    def process_title_common(self, line):
        if line.startswith("  + Main Feature"):
            vprint(3, "Main feature!")
            self.current_title.main_feature = True
            return True
        match = self.re_autocrop.match(line)
        if match:
            self.current_title.autocrop = match.group(1)
            vprint(3, "autocrop = %s" % self.current_title.autocrop)
            return True
        match = self.re_duration.match(line)
        if match:
            self.current_title.duration = match.group(1)
            vprint(3, "duration = %s" % self.current_title.duration)
            return True
        match = self.re_size.match(line)
        if match:
            self.current_title.size = match.group(1)
            self.current_title.pixel_aspect = match.group(2)
            self.current_title.display_aspect = match.group(3)
            self.current_title.fps = match.group(4)
            vprint(3, "display aspect = %s" % self.current_title.display_aspect)
            return True
        return False
    
    def process_title_audio(self, line):
        return False
    
    def process_title_subtitle(self, line):
        return False
    
    def process_title_subclass(self, line):
        return False
    
    def process_stream(self, line):
        return False



class FullDvdBackupParser(HandBrakeScanParser):
    re_scan_num_title = re.compile("(\[.+\])? scan: DVD has (\d+) title")
    re_audio = re.compile("(\[.+\])? scan: checking audio (\d+)")
    re_dvd_stream_id = re.compile("(\[.+\])? scan: id=(?:0x)?([0-9a-f]+)bd, lang=(.+), 3cc=([a-z]+)")
    re_subtitle = re.compile("(\[.+\])? scan: checking subtitle (\d+)")
    re_preview_audio = re.compile("(\[.+\])? scan: audio 0x([0-9a-f]+): (.+), rate=(\d+)Hz, bitrate=(\d+) (.+)")
    re_vts = re.compile("  \+ vts (\d+), ttn (\d+), (.+)")
    
    @classmethod
    def works_with(cls, output):
        for line in output.splitlines():
            match = cls.re_scan_num_title.match(line)
            if match:
                return True
        return False
    
    def process_line_subclass(self, line):
        match = self.re_scan_num_title.match(line)
        if match:
            self.scan.num_titles = int(match.group(2))
            vprint(3, "matched! num titles=%d" % self.scan.num_titles)
            return True
        return False
    
    def process_title_audio(self, line):
        match = self.re_audio.match(line)
        if match:
            order = int(match.group(2))
            vprint(3, "matched! audio=%d" % order)
            self.current_stream = Audio(order)
            self.current_title.audio.append(self.current_stream)
            return True
        match = self.re_preview_audio.match(line)
        if match:
            hex_id = match.group(2)
            if hex_id.endswith('bd'):
                hex_id = hex_id[0:2]
            id = int(hex_id, 16)
            vprint(3, "matched! preview audio=%d" % id)
            audio = self.current_title.find_audio_by_mplayer_id(id)
            if audio is None:
                order = len(self.current_title.audio) + 1
                vprint(0, "failed matching audio stream %d.  HandBrake scan output probably changed. Assuming it is stream #%d" % (id, order))
                audio = Audio(order)
                self.current_title.audio.append(audio)
                audio.mplayer_id = id
            audio.rate = int(match.group(4))
            audio.bitrate = int(match.group(5))
            audio.codec = match.group(6)
            return True
        return False
    
    def process_title_subtitle(self, line):
        match = self.re_subtitle.match(line)
        if match:
            order = int(match.group(2))
            vprint(3, "matched! subtitle=%d" % order)
            self.current_stream = Subtitle(order)
            self.current_title.subtitle.append(self.current_stream)
            return True
        return False
    
    def process_title_subclass(self, line):
        match = self.re_vts.match(line)
        if match:
            self.current_title.vts = int(match.group(1))
            vprint(3, "vts = %d" % self.current_title.vts)
            return True
        return False
    
    def process_stream(self, line):
        match = self.re_dvd_stream_id.match(line)
        if match:
            id = int(match.group(2), 16)
            vprint(3, "matched dvd stream! id=%d" % id)
            self.current_stream.mplayer_id = id
            self.current_stream.lang = match.group(3)
            if not self.current_stream.name:
                self.current_stream.name = self.get_interesting_name(self.current_stream.lang)
            self.current_stream.threecc = match.group(4)
            return True
        return False

HandBrakeScanParser.register(FullDvdBackupParser)


class MakeMkvDirParser(HandBrakeScanParser):
    re_mkv_input = re.compile("Input #(\d+)\, matroska.+")
    re_mkv_stream_id = re.compile(".+Stream #\d+\.(\d+)\((.+)\): ([a-zA-Z]+): .+")
    re_mkv_stream_filename = re.compile("  \+ stream: (.+)")
    re_mkv_title_num_begin = re.compile("t([0-9]+)_.+\.mkv")
    re_mkv_title_num_end = re.compile(".+t([0-9]+)\.mkv")
    
    @classmethod
    def works_with(cls, output):
        for line in output.splitlines():
            match = cls.re_mkv_input.match(line)
            if match:
                return True
        return False
    
    def parse_init(self):
        self.mkv_counters = {'Video': 1, 'Audio': 1, 'Subtitle': 1}
    
    def process_title_init(self, line):
        self.mkv_counters['Video'] = 1
        self.mkv_counters['Audio'] = 1
        self.mkv_counters['Subtitle']= 1

    def process_line_subclass(self, line):
        match = self.re_mkv_stream_filename.match(line)
        if match:
            filename = match.group(1)
            vprint(3, "matched! mkv stream=%s" % filename)
            self.current_title.rel_pathname = filename
            
            basename = os.path.basename(filename)
            match = self.re_mkv_title_num_begin.match(basename)
            if match:
                self.current_title.user_title_num = int(match.group(1))
            else:
                match = self.re_mkv_title_num_end.match(basename)
                if match:
                    self.current_title.user_title_num = int(match.group(1))
            return True
    
    def process_title_subclass(self, line):
        match = self.re_mkv_stream_id.match(line)
        if match:
            id = int(match.group(1))
            self.stream_flag = match.group(3)
            order = self.mkv_counters.get(self.stream_flag, 0)
            vprint(3, "matched mkv %s stream! order=%d, stream_num=%d mplayer_id=%d" % (self.stream_flag, order, id, order-1))
            if self.stream_flag == "Audio":
                self.current_stream = Audio(order)
                self.current_title.audio.append(self.current_stream)
                vprint(1, "Adding audio %d to %s" % (order, self.current_title))
            elif self.stream_flag == "Subtitle":
                self.current_stream = Subtitle(order)
                self.current_title.subtitle.append(self.current_stream)
            elif self.stream_flag == "Video":
                return True
            else:
                vprint(0, "ignoring mkv stream type %s" % self.stream_flag)
            self.mkv_counters[self.stream_flag] += 1
            self.current_stream.mplayer_id = order - 1
            self.current_stream.lang = match.group(2)
            if not self.current_stream.name:
                self.current_stream.name = self.current_stream.lang
            self.current_stream.threecc = match.group(2)
            return True

HandBrakeScanParser.register(MakeMkvDirParser)
