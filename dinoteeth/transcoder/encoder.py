import os, re, time
from threading import Thread
from Queue import Queue, Empty

from common import *
from audio import MkvAudioExtractor, VOBAudioExtractor, AudioGain
from mkv import MkvScanner, MkvPropEdit
from ..utils import vprint
from .. import settings

class HandBrakeEncoder(HandBrake):
    def __init__(self, source, scan, output, dvd_title, audio_spec, subtitle_spec, options, audio_only=False, bonus=False):
        HandBrake.__init__(self, source)
        self.source = source
        self.scan = scan
        self.title_num = dvd_title
        self.output = output
        self.title = scan.get_user_title(self.title_num)
        if not self.title.is_valid():
            raise HandBrakeScanError()
        self.options = options
        self.audio_only = audio_only
        
        self.args = self.title.handbrake_source(source)
        self.select_audio(audio_spec)
        self.select_subtitles(subtitle_spec)
        self.add_options(options, bonus)
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
            audio = self.title.find_audio_by_handbrake_id(track)
            if audio is None:
                wprint("Title %d: Invalid audio track %s (%s); skipping" % (self.title_num, track, name))
            else:
                tracks.append(track)
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
            names.append("Stereo (%s)" % default.threecc)
            commentary_count = 0
            for audio in default_set[1:]:
                if "Commentary" in audio.name:
                    tracks.append(audio.order)
                    commentary_count += 1
                    names.append("Commentary %d (%s)" % (commentary_count, audio.threecc))
        
        self.audio_track_order = tracks
        
        self.args.extend(["-a", ",".join([str(t) for t in tracks]),
                             "-A", ",".join(names)])
    
    def select_subtitles(self, track_titles):
        tracks = []
        names = []
        scan = False
        for track, name in track_titles.iter_tracks():
            sub = self.title.find_subtitle_by_handbrake_id(track)
            if sub is None:
                wprint("Title %d: Invalid subtitle track %s (%s); skipping" % (self.title_num, track, name))
            else:
                tracks.append(track)
                if name:
                    # Override stream name to user's name
                    sub.name = name
                else:
                    name = sub.name
                names.append(name)
        
        if not tracks:
            burnable = []
            cc = None
            default_set = self.title.find_subtitle_by_language()
            for sub in default_set:
                if sub.is_burnable():
                    burnable.append(sub)
                if cc is None and sub.type == "cc":
                    cc = sub
            if burnable:
                tracks.extend([v.order for v in burnable])
                names.append([v.lang for v in burnable])
            if cc is not None:
                if self.options.cc_first:
                    tracks[0:0] = [cc.order]
                    names[0:0] = [cc.lang]
                else:
                    tracks.append(cc.order)
                    names.append(cc.lang)
        
        self.subtitle_track_order = tracks[:]

        if self.title.scanable_subtitles:
            for track in tracks:
                sub = self.title.find_subtitle_by_handbrake_id(track)
                if sub.is_burnable():
                    scan = True
                    tracks[0:0] = ["scan"]
                    break
        
        self.args.extend(["-s", ",".join([str(t) for t in tracks])])
        if scan:
            self.args.extend(["-F", "1", "--subtitle-burn", "1"])
    
    def add_options(self, options, bonus):
        self.args.append("-m") # include chapter markers
        if options.preview > 0:
            self.args.extend(["-c", "1-%d" % options.preview])
        if options.fast or self.audio_only:
            self.args.extend(["-r", "5"])
            self.args.extend(["-b", "100"])
            self.args.extend(["-w", "160"])
        else:
            self.args.extend(["-2", "-T", "--detelecine"])
            if options.decomb:
                self.args.append("--decomb")
            self.args.extend(("-e", options.video_encoder))
            if options.x264_preset:
                self.args.extend(("--x264-preset", options.x264_preset))
            if options.x264_tune:
                self.args.extend(("--x264-tune", options.x264_tune))
            
            width, height = self.title.size.split("x")
            width = int(width)
            print width
            if width > 720:
                if options.hd_width > 0:
                    width = options.hd_width
                elif settings.hd_width > 0:
                    width = settings.hd_width
                if width >= 1920:
                    bitrate = settings.hd_1080_video_bitrate
                elif width >= 1360:
                    bitrate = settings.hd_768_video_bitrate
                elif width >= 1280:
                    bitrate = settings.hd_720_video_bitrate
                else:
                    bitrate = settings.hd_560_video_bitrate
                self.args.extend(("-w", str(width)))
            else:
                bitrate = settings.sd_video_bitrate
                if self.title.display_aspect in ["16x9", "1.78", "1.77"]:
                    self.args.extend(("--display-width", "854"))
                elif self.title.display_aspect in ["4x3", "1.33"]:
                    self.args.extend(("--pixel-aspect", "8:9"))
                else:
                    raise RuntimeError("Unknown standard definition aspect ratio %s" % self.title.display_aspect)
                self.args.append("--loose-anamorphic")
            if options.video_bitrate > 0:
                bitrate = options.video_bitrate
            if bonus:
                bitrate = int(bitrate * settings.bonus_bitrate_scale)
            self.args.extend(("-b", str(bitrate)))
        if options.grayscale:
            self.args.append("-g")
        which = options._latest_of("crop", "autocrop")
        if which == "autocrop":
            self.args.extend(["--crop", self.title.autocrop])
        else:
            self.args.extend(["--crop", options.crop])
        
        # Audio settings
        encoder = settings.audio_encoder
        if options.audio_encoder:
            encoder = options.audio_encoder
        self.args.extend(("-E", encoder))
        bitrate = settings.audio_bitrate
        if options.audio_bitrate > 0:
            bitrate = options.audio_bitrate
        self.args.extend(("-B", str(bitrate)))
    
    def enqueue_output(self, out, queue):
        for line in iter(out.readline, ''):
            queue.put(line)
        out.close()
    
    def run(self):
        if not self.options.overwrite and os.path.exists(self.output):
            self.vprint(0, "-skipping already encoded file %s; use --overwrite to replace existing files" % self.output)
            return 
        self.vprint(0, "-Using HandBrake to encode video %s" % self.output)
        self.compute_gains()
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
                    self.vprint(2, "stdout-->%s<--" % line.rstrip())
            except Empty:
                self.vprint(3, "stdout empty")
            try:
                while True and error is None:
                    line = q_stderr.get_nowait()
                    error = out.process(line)
                    self.vprint(2, "-->%s<--" % line.rstrip())
                    if not line:
                        break
            except Empty:
                self.vprint(3, "stderr empty")
            time.sleep(1)
            self.vprint(3, "Poll: %s" % str(p.poll()))
        if error is not None:
            self.vprint(0, "-HandBrake encoding failed.")
            p.terminate()
        self.vprint(3, "Waiting for process to finish...")
        p.wait()
        self.vprint(3, "Waiting for thread join...")
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
        return normalizer.gains
    
    def compute_gains_mplayer(self):
        vprint(0, "-Preparing to compute audio gain factors")
        extractor = VOBAudioExtractor(self.source, self.title, self.audio_track_order, self.output)
        extractor.run()
        normalizer = AudioGain(self.output, extractor=extractor)
        normalizer.run()
#        txt = """Computing levels...
#  level        peak         gain
#-31.6890dBFS  -9.100dBFS 19.6890dB  tmp.Roxanne.mkv.0.wav                 
#"""
#        normalizer = AudioGain(self.output, gains_output=txt)
        return normalizer.gains
    
    def compute_gains(self):
        if self.audio_only:
            return
        gains = []
        if self.options.gain:
            gains = str(self.options.gain).split(",")
        elif self.options.normalize:
            gains = self.compute_gains_mplayer()
        if gains:
            self.args.append("--gain")
            self.args.extend([",".join(gains)])
            if self.options.hb_normalize:
                norm = []
                for gain in gains:
                    if float(gain) > 0:
                        norm.append("1")
                    else:
                        norm.append("0")
                self.args.append("--normalize-mix")
                self.args.extend([",".join(norm)])

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
        elif line.startswith("ERROR:"):
            _, error = line.split(": ", 1)
            vprint(0, "** HandbrakeCLI error: %s" % error)
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
