import os

from ..utils import ExeRunner, vprint

class MkvAudioExtractor(ExeRunner):
    exe_name = "mkvextract"
    
    def setCommandLine(self, source, mkv=None, options=None, *args, **kwargs):
        self.args = ["tracks", source]
        self.handbrake_to_mp3 = dict()
        for handbrake_id, mkv_id in mkv.handbrake_to_mkv.iteritems():
            output = "tmp.%s.%d.mp3" % (source, handbrake_id)
            self.args.append("%d:%s" % (mkv_id, output))
            self.handbrake_to_mp3[handbrake_id] = output

class MplayerAudioExtractor(ExeRunner):
    exe_name = "mplayer"
    
    def setCommandLine(self, source, output="", aid=128, options=None, *args, **kwargs):
        self.args = ["-nocorrect-pts", "-quiet", "-vc", "null", "-vo", "null",
                     "-ao", "pcm:fast:file=%s" % output, "-aid", str(aid), source]

class VOBAudioExtractor(object):
    def __init__(self, source, title, track_order, output):
        self.handbrake_to_mp3 = dict()
        self.source = source
        self.title = title
        self.url = title.mplayer_cmd(source)
        self.track_order = track_order
        self.output = output
        
    def run(self):
        vprint(0, "-Using mplayer to rip audio tracks from %s" % self.url)
        handbrake_id = 0
        for order in self.track_order:
            handbrake_id += 1
            vprint(0, "--Ripping audio track %d" % order)
            stream = self.title.find_audio_by_handbrake_id(order)
            #print stream
            output = "tmp.%s.%d.wav" % (self.output, handbrake_id)
            self.handbrake_to_mp3[handbrake_id] = output
            wav = MplayerAudioExtractor(self.url, output=output, aid=stream.mplayer_id)
            wav.run()
    
    def cleanup(self):
        for h_id, filename in self.handbrake_to_mp3.iteritems():
            os.remove(filename)

class AudioGain(ExeRunner):
    exe_name = "normalize"
    
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
