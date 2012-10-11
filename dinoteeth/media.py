import os, sys, re, bisect, time, glob
from datetime import datetime

from persistent import Persistent
from database import commit

import utils

from third_party.guessit import guess_file_info, Guess
from third_party import enzyme


def enzyme_scan(path):
    try:
        scan = enzyme.parse(path)
    except:
        for (parser_name, parser_mimetypes, parser_extensions) in enzyme.PARSERS:
            mod = __import__("third_party.enzyme.%s" % parser_name, globals=globals(), locals=locals(), fromlist=[parser_name], level=-1)
            try:
                with open(path, 'rb') as f:
                    scan = mod.Parser(f)
                    break
            except enzyme.ParseError, e:
                #print "Not %s" % parser_name
                pass
    # Some enzyme scanners maintain a reference to a file handle -- it must be
    # removed in order for the instance to be pickled.
    scan.file = None
    return scan

def enzyme_extensions():
    extensions = []
    for (parser_name, parser_mimetypes, parser_extensions) in enzyme.PARSERS:
        extensions.extend(parser_extensions)
    return extensions


class TitleKey(Persistent):
    def __init__(self, category, title, year, subcategory):
        self.category = category
        self.title = title
        self.year = year
        self.subcategory = subcategory

    def __str__(self):
        return str(self.__dict__)

    def __hash__(self): 
        return hash((self.category, self.title, self.year, self.subcategory))

    def __eq__(self, other): 
        return self.__dict__ == other.__dict__


class MediaScan(Persistent):
    ignore_leading_articles = ["a", "an", "the"]
    subtitle_file_extensions = []
    percent_considered_complete = 0.96
    
    def __init__(self, pathname, flags=""):
        self.pathname = pathname
        self.flags = flags
        self.play_date = None
        self.position = 0
        self.reset()
    
    def __str__(self):
        return "%s: %s %d audio, %d subtitles, length=%s, mtime=%d" % (self.pathname, self.type, len(self.audio), len(self.subtitles), self.length, self.mtime)
    
    def __cmp__(self, other):
        return cmp(self.sort_key(), other.sort_key())
    
    def sort_key(self):
        g = self.guess
        t = self.title.lower()
        for article in self.ignore_leading_articles:
            a = "%s " % article.lower()
            if t.startswith(a):
                t = t[len(a):] + ", %s" % t[0:len(article)]
                break
        return (t,
             g.get('season', 0),
             g.get('episodeNumber', 9999),
             g.get('bonusNumber', 0),
             g.get('bonusTitle', ""),
             )
    
    def reset(self):
        # Rather than saving a copy of the entire Enzyme scan, just save the
        # parts that we are going to use later.  This reduces database size by
        # almost an order of magnitude
        scan = enzyme_scan(self.pathname)
        self.audio = scan.audio
        self.subtitles = scan.subtitles
        self.length = scan.length
        
        self.selected_audio_id = 0
        self.selected_subtitle_id = 0
        
        if os.path.exists(self.pathname):
            self.mtime = os.stat(self.pathname).st_mtime
        else:
            self.mtime = -1
        
        if "basename" in self.flags:
            name = os.path.basename(self.pathname)
        else:
            name = self.pathname
        name = utils.decode_title_text(name)
        if "series" in self.flags or "episode" in self.flags:
            category = "episode"
        elif "movie" in self.flags:
            category = "movie"
        else:
            category = "autodetect"
        self.guess = guess_file_info(name, category)
        self.metadata = None
    
    def is_current(self):
        if os.path.exists(self.pathname):
            print self.pathname, os.stat(self.pathname).st_mtime, self.mtime
            if os.stat(self.pathname).st_mtime == self.mtime:
                return True
        return False
    
    def iter_audio(self):
        for a in self.audio:
            yield a
    
    def iter_subtitles(self):
        for s in self.subtitles:
            yield s
    
    def get_audio_options(self):
        options = []
        for i, audio in enumerate(self.iter_audio()):
#            print "audio track: %s" % audio
            title = audio.title
            if not title:
                channels = audio.channels
                if not channels:
                    title = "Audio Track %d" % (i + 1)
                else:
                    if audio.channels == 1:
                        title = "Mono"
                    elif audio.channels == 2:
                        title = "Stereo"
                    else:
                        title = "%d Channels" % audio.channels
            options.append((i, i == self.selected_audio_id, title))
        if not options:
            # "No audio" is not an option by default; only if there really is
            # no audio available in the media
            options.append((-1, True, "No audio"))
        return options
    
    def set_audio_options(self, id=-1, **kwargs):
        self.selected_audio_id = id
        print "FIXME: audio index = %s" % self.selected_audio_id
    
    def next_option(self, options):
        index = 0
        for id, selected, _ in options:
            if selected:
                break
            index += 1
        item = options.pop(0)
        options.append(item)
        return options[index][0]
    
    def next_audio(self):
        self.selected_audio_id = self.next_option(self.get_audio_options())
    
    def get_external_subtitles(self):
        paths = []
        base, _ = os.path.splitext(self.pathname)
        for ext in self.subtitle_file_extensions:
            subs = set(glob.glob("%s*%s" % (base, ext)))
            
            # If the plain "file.ext" exists, it will be first.  All others
            # with more info (e.g.  "file-lang1.ext") in the filename will
            # be sorted.
            first = base + ext
            if first in subs:
                paths.append(first)
                subs.remove(first)
            subs = sorted(subs)
            paths.extend(subs)
        return paths
    
    def is_subtitle_external(self, id):
        return id >= len(self.subtitles)
    
    def get_subtitle_path(self, id):
        id = id - len(self.subtitles)
        external = self.get_external_subtitles()
        if id < len(external):
            return external[id]
        return None
    
    def get_subtitle_options(self):
        # Unlike audio, "No subtitles" should always be an option in case
        # people don't want to view subtitles
        options = [(-1, -1 == self.selected_subtitle_id, "No subtitles")]
        i = 0
        for i, subtitle in enumerate(self.iter_subtitles()):
#            print "subtitle track: %s" % subtitle
            options.append((i, i == self.selected_subtitle_id, subtitle.title))
        external = self.get_external_subtitles()
        for path in external:
            options.append((i, i == self.selected_subtitle_id, os.path.basename(path)))
            i += 1
        return options
    
    def set_subtitle_options(self, id=-1, **kwargs):
        self.selected_subtitle_id = id
        print "FIXME: subtitle index = %s" % self.selected_subtitle_id
    
    def next_subtitle(self):
        self.selected_subtitle_id = self.next_option(self.get_subtitle_options())
    
    def get_runtime(self):
        return utils.time_format(self.length)
    
    def get_title(self):
        if self.guess['type'] == "episode" and 'series' in self.guess:
            return self.guess['series']
        elif 'title' in self.guess:
            return  self.guess['title']
        return os.path.basename(self.pathname)
    
    title = property(get_title)
    
    def get_type(self):
        if self.guess['type'] == "episode":
            return "series"
        return "movie"
    
    type = property(get_type)
    
    def get_title_key(self):
        try:
            year = self.guess['year']
        except KeyError:
            year = None
        #return self.get_title(), year, self.get_type()
        return TitleKey("video", self.get_title(), None, self.get_type())
    
    title_key = property(get_title_key)
    
    def get_season(self):
        return self.guess.get('season', 0)
    
    season = property(get_season)
    
    def get_episode(self):
        return self.guess.get('episodeNumber', 0)
    
    episode = property(get_episode)
    
    def is_bonus(self):
        return 'bonusNumber' in self.guess or 'bonusTitle' in self.guess
    
    def get_bonus_title(self):
        bonus = None
        g = self.guess
        if 'bonusNumber' in g:
            if 'bonusTitle' not in g:
                bonus = "Bonus Feature %s" % str(g['bonusNumber'])
            else:
                bonus = "#%s: %s" % (str(g['bonusNumber']), str(g['bonusTitle']))
        elif 'bonusTitle' in g:
            bonus = str(g['bonusTitle'])
        return bonus
    
    def get_episode_title(self):
        title = self.get_bonus_title()
        if title is None:
            g = self.guess
            title = "Episode %d" % g['episodeNumber']
            eptitle = g.get('episodeTitle',"")
            if eptitle:
                title += " " + eptitle
        return title
    
    episode_title = property(get_episode_title)
    
    def get_display_title(self):
        title = self.get_bonus_title()
        if title is None:
            g = self.guess
            if 'episodeNumber' in g:
                title = self.get_episode_title()
            elif 'episodeTitle' in g:
                title = g['episodeTitle']
            else:
                title = "Main Feature"
        title += " (%s)" % self.get_runtime()
        return title
    
    display_title = property(get_display_title)

    def get_film_number(self):
        return self.guess.get('filmNumber', 1)
    
    film_number = property(get_film_number)

    def is_considered_complete(self, last_pos):
        return last_pos >= self.percent_considered_complete * self.length

    def set_last_position(self, last_pos):
        if self.is_considered_complete(last_pos):
            last_pos = -1.0
        self.play_date = datetime.utcnow()
        self.position = last_pos
        commit()

    def get_last_position(self):
        return self.position
    
    def is_paused(self):
        return self.position > 0
    
    def paused_at_text(self):
        seconds = int(self.position)
        return utils.time_format(seconds)
    
    def get_last_played_stats(self):
        if self.play_date is not None:
            date = utils.time_since(self.play_date)
            if self.position > 0:
                return date, "%2d%%, elapsed time %s" % (self.position * 100 / self.length, utils.time_format(self.position))
            else:
                return date, None
        return None, "Never played"


if __name__ == "__main__":
    import sys
    from database import DBFacade
    
    db = DBFacade("Data.fs")
    scans = db.get_mapping("scans")
    
    for file in sys.argv[1:]:
        if file not in scans:
            print file
            scan = MediaScan(file)
            scans[file] = scan
            db.commit()
        else:
            scan = scans[file]
        print scan
