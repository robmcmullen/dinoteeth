from ..utils import ExeRunner

class MkvScanner(ExeRunner):
    exe_name = "mkvmerge"
    
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
    exe_name = "mkvpropedit"
    
    def setCommandLine(self, source, dvd_title=1, scan=None, mkv=None, encoder=None, options=None, *args, **kwargs):
        self.vprint(0, "-Using mkvpropedit to add names to tracks")
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
