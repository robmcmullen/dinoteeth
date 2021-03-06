import os, sys, glob
from datetime import datetime

from persistent import Persistent

from .. import utils
from .. import settings

from guessit import guess_file_info


class AVScanBase(Persistent):
    category = "video"
    subcat = None
    ignore_leading_articles = ["a", "an", "the"]
    percent_considered_complete = 0.96
    
    @classmethod
    def guess(cls, file, info):
        if "basename" in file.flags:
            name = os.path.basename(file.pathname)
        else:
            name = file.pathname
        name = utils.decode_title_text(name)
        if "series" in file.flags or "episode" in file.flags:
            subcat = "episode"
        elif "movie" in file.flags:
            subcat = "movie"
        else:
            subcat = "autodetect"
        guess = guess_file_info(name, subcat)
        if guess['type'] == "episode":
            return SeriesScan(file, info, guess)
        return MovieScan(file, info, guess)
        
    def __init__(self, file, info, guess):
        self.play_date = None
        self.position = 0
        self.init_common(file, info, guess)
        self.init_attributes(file, info, guess)
        self.display_title = self.calc_display_title(file, info, guess)
        self.title_key = self.calc_title_key(file, info, guess)
    
    def __str__(self):
        try:
            v = self.video[0]
            return "%s/%s %dx%d %s video, %d audio, %d subtitles, length=%s" % (self.category, self.subcat, v.width, v.height, v.codec, len(self.audio), len(self.subtitles), self.length)
        except:
            return "%s/%s %d audio, %d subtitles, length=%s" % (self.category, self.subcat, len(self.audio), len(self.subtitles), self.length)
    
    def sort_key(self):
        """Return a 5-tuple:
        
        name
        season
        episode number
        bonus number
        bonus title
        """
        raise RuntimeError("abstract method")
    
    def copy_stats_from(self, old_scan):
        self.position = old_scan.position
        self.play_date = old_scan.play_date
        self.selected_audio_id = old_scan.selected_audio_id
        self.selected_subtitle_id = old_scan.selected_subtitle_id
    
    def init_attributes(self, file, info, guess):
        pass
    
    def init_bonus(self, file, info, guess):
        if 'bonusNumber' in guess or 'bonusTitle' in guess:
            self.is_bonus = True
        else:
            self.is_bonus = False
        self.bonus_title = self.calc_bonus_title(file, info, guess)
        self.bonus_number = guess.get('bonusNumber', 0)
    
    def calc_bonus_title(self, file, info, guess):
        bonus = None
        g = guess
        if 'bonusNumber' in g:
            if 'bonusTitle' not in g:
                bonus = "Bonus Feature %s" % str(g['bonusNumber'])
            else:
                bonus = "#%s: %s" % (str(g['bonusNumber']), str(g['bonusTitle']))
        elif 'bonusTitle' in g:
            bonus = str(g['bonusTitle'])
        return bonus
    
    def calc_title_key(self, file, info, guess):
        try:
            year = guess['year']
        except KeyError:
            year = None
        #return TitleKey(self.category, self.subcat, self.title, year)
        return utils.TitleKey(self.category, self.subcat, self.title, None)
    
    def init_common(self, file, info, guess):
        # Rather than saving a copy of the entire metadata scan, just save the
        # parts that we are going to use later.  This reduces database size by
        # an order of magnitude
        self.video = []
        for i, v in enumerate(info.video):
            self.video.append({
                'codec': v.codec,
                'fourcc': v.fourcc,
                'width': v.width,
                'height': v.height,
                'id': v.id,
                })
        
        self.audio = []
        for i, a in enumerate(info.audio):
            title = a.title
            if not title:
                channels = a.channels
                if not channels:
                    title = "Audio Track %d" % (i + 1)
                else:
                    if a.channels == 1:
                        title = "Mono"
                    elif a.channels == 2:
                        title = "Stereo"
                    else:
                        title = "%d Channels" % a.channels
            self.audio.append({
                'title': title,
                'channels': a.channels,
                'codec': a.codec,
                'id': a.id,
                })
        
        self.subtitles = []
        for s in info.subtitles:
            self.subtitles.append({
                'title': s.title,
                'codec': s.codec,
                'id': s.id,
                })
        
        self.length = info.length
        
        self.selected_audio_id = 0
        self.selected_subtitle_id = None
        
        self.title = self.calc_title(file, info, guess)
        self.init_bonus(file, info, guess)
    
    def iter_audio(self):
        for a in self.audio:
            yield a
    
    def iter_subtitles(self):
        for s in self.subtitles:
            yield s
    
    def get_audio_options(self):
        options = []
        for i, audio in enumerate(self.iter_audio()):
            options.append((i, i == self.selected_audio_id, audio['title']))
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
    
    def get_external_subtitles(self, pathname):
        paths = []
        base, _ = os.path.splitext(pathname)
        for ext in settings.subtitle_file_extensions:
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
    
    def get_subtitle_path(self, id, pathname):
        id = id - len(self.subtitles)
        external = self.get_external_subtitles(pathname)
        if id < len(external):
            return external[id]
        return None
    
    def get_subtitle_options(self, pathname):
        # Default subtitle display based on user settings
        if self.selected_subtitle_id is None:
            if settings.default_subtitles:
                self.selected_subtitle_id = 0
            else:
                self.selected_subtitle_id = -1
            print "default: %s => %s" % (settings.default_subtitles, self.selected_subtitle_id)
                
        # Unlike audio, "No subtitles" should always be an option in case
        # people don't want to view subtitles
        options = [(-1, -1 == self.selected_subtitle_id, "No subtitles")]
        i = 0
        for i, subtitle in enumerate(self.iter_subtitles()):
#            print "subtitle track: %s" % subtitle
            options.append((i, i == self.selected_subtitle_id, subtitle['title']))
        external = self.get_external_subtitles(pathname)
        for path in external:
            options.append((i, i == self.selected_subtitle_id, os.path.basename(path)))
            i += 1
        return options
    
    def set_subtitle_options(self, id=-1, **kwargs):
        self.selected_subtitle_id = id
        print "FIXME: subtitle index = %s" % self.selected_subtitle_id
    
    def next_subtitle(self, pathname):
        self.selected_subtitle_id = self.next_option(self.get_subtitle_options(pathname))
    
    def get_runtime(self):
        return utils.time_format(self.length)
    
    def is_considered_complete(self, last_pos):
        return last_pos >= self.percent_considered_complete * self.length

    def set_last_position(self, last_pos=-1.0):
        if self.is_considered_complete(last_pos):
            last_pos = -1.0
        retry = 3
        while retry > 0:
            self.play_date = datetime.utcnow()
            self.position = last_pos
            try:
                utils.DBFacade.commit()
                print "Updated position"
                return
            except:
                utils.DBFacade.abort()
            
            import time
            print "Retrying..."
            time.sleep(.2)
            retry -= 1

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

class MovieScan(AVScanBase):
    subcat = "movie"

    def calc_title(self, file, info, guess):
        if 'title' in guess:
            return guess['title']
        return os.path.basename(file.pathname)
    
    def init_attributes(self, file, info, guess):
        self.film_number = self.calc_film_number(file, info, guess)
        
    def sort_key(self):
        """Return a 5-tuple:
        
        season
        episode number
        bonus number
        name
        bonus title
        """
        t = self.title.lower()
        for article in self.ignore_leading_articles:
            a = "%s " % article.lower()
            if t.startswith(a):
                t = t[len(a):] + ", %s" % t[0:len(article)]
                break
        key = (0, self.bonus_number, 0, t, self.bonus_title)
        return key

    def calc_film_number(self, file, info, guess):
        return guess.get('filmNumber', 1)
    
    def calc_display_title(self, file, info, guess):
        if self.is_bonus:
            title = self.bonus_title
        else:
            title = "Main Feature"
        title += " (%s)" % self.get_runtime()
        return title


class SeriesScan(AVScanBase):
    subcat = "series"
        
    def sort_key(self):
        """Return a 5-tuple:
        
        season
        episode number
        bonus number
        name
        bonus title
        """
        t = self.title.lower()
        for article in self.ignore_leading_articles:
            a = "%s " % article.lower()
            if t.startswith(a):
                t = t[len(a):] + ", %s" % t[0:len(article)]
                break
        return (self.season, self.bonus_number, self.episode, t, self.bonus_title)

    def calc_title(self, file, info, guess):
        if 'series' in guess:
            return guess['series']
        return os.path.basename(file.pathname)
    
    def init_attributes(self, file, info, guess):
        self.season = self.calc_season(file, info, guess)
        self.episode = self.calc_episode(file, info, guess)
        self.episode_title = self.calc_episode_title(file, info, guess)

    def calc_season(self, file, info, guess):
        return guess.get('season', 0)
    
    def calc_episode(self, file, info, guess):
        return guess.get('episodeNumber', 0)
    
    def calc_episode_title(self, file, info, guess):
        if self.is_bonus:
            title = self.bonus_title
        else:
            title = "Episode %d" % self.episode
            eptitle = guess.get('episodeTitle',"")
            if eptitle:
                title += " " + eptitle
        return title
    
    def calc_display_title(self, file, info, guess):
        if self.is_bonus:
            title = self.bonus_title
        else:
            if 'episodeNumber' in guess:
                title = self.episode_title
            elif 'episodeTitle' in guess:
                title = guess['episodeTitle']
            else:
                title = "Episode"
        title += " (%s)" % self.get_runtime()
        return title


from ..filescan import MediaFile
MediaFile.register("MEDIA_AV", AVScanBase)
