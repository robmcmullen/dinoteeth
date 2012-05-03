from ..utils import ExeRunner, vprint

def wprint(text):
    print "WARNING: %s" % text

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
        self.autocrop = "0/0/0/0"
        self.size = ""
        self.pixel_aspect = ""
        self.display_aspect = ""
        self.fps = ""
        self.audio = []
        self.subtitle = []
    
    def is_valid(self):
        return bool(self.size)
    
    def __str__(self):
        s = "title %d: %s " % (self.title_num, self.duration)
        if self.main_feature:
            s += "(MAIN) "
        s += "%s, %s " % (self.size, self.display_aspect)
        if self.autocrop != "0/0/0/0":
            s += "(autocrop %s) " % self.autocrop
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
    
    def find_subtitle_by_handbrake_id(self, id):
        for sub in self.subtitle:
            if sub.order == id:
                return sub
    
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
            # Note: only one closed caption track can exist and it doesn't have
            # an mplayer id number
            if sub.mplayer_id == -1 and sub.type == "vobsub":
                vprint(1, "Found inactive subtitle %d" % sub.order)
            else:
                cleaned.append(sub)
        self.subtitle = cleaned

class HandBrakeScanError(RuntimeError):
    pass

class HandBrake(ExeRunner):
    exe_name = "HandBrakeCLI"

    def setCommandLine(self, source, options=None, *args, **kwargs):
        args = list(args)
        args.extend(['-i', source])
        ExeRunner.setCommandLine(self, None, *args, **kwargs)
