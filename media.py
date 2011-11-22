import os, sys, glob, re
import pyglet

from model import MenuDetail
import utils

from guessit import guess_file_info, Guess


class MediaDetail(MenuDetail):
    def __init__(self, pathname, title):
        MenuDetail.__init__(self, "")
        self.fullpath = pathname
        self.dirname, self.filename = os.path.split(pathname)
        self.fileroot, self.fileext = os.path.splitext(self.filename)
        self.title = title
        self.detail_image = None
        self.attempted_detail_image_load = False
    
    def get_full_title(self):
        return unicode(self.title)
    
    def get_feature_title(self):
        return self.title.title
    
    def get_episode_name(self):
        return self.title.episode_name
    
    # Overriding get_detail_image to perform lazy image lookup 
    def get_detail_image(self):
        if self.detail_image is None and not self.attempted_detail_image_load:
            imagedir = os.path.join(self.dirname, ".thumbs")
            for ext in [".jpg", ".png"]:
                imagepath = os.path.join(imagedir, self.fileroot + ext)
                print "checking %s" % imagepath
                if os.path.exists(imagepath):
                    self.detail_image = pyglet.image.load(imagepath)
                    print "loaded %s" % imagepath
                    break
            self.attempted_detail_image_load = True
        return self.detail_image
    
    # Placeholder for IMDB lazy lookup
    def get_description(self):
        return "Details for %s" % self.title
    
    def is_playable(self):
        return False


class GuessitDetail(MediaDetail):
    def __init__(self, guess):
        MediaDetail.__init__(self, guess['pathname'], "")
        self.guess = guess
    
    def get_extra_title(self):
        text = []
        g = self.guess
        if 'extraNumber' in g:
            text.append("Bonus Feature %s" % g['extraNumber'])
        if 'extraTitle' in g:
            text.append(g['extraTitle'])
        return unicode(" ".join(text))

class MovieDetail(GuessitDetail):
    def get_full_title(self):
        title = [self.guess['title'], self.get_extra_title()]
        return unicode(" ".join(title))
    
    def get_feature_title(self):
        return self.guess['title']
    
    def get_episode_name(self):
        return self.guess.get('extraTitle', '<none>')
    
    def is_playable(self):
        return True

class EpisodeDetail(GuessitDetail):
    def get_episode_title(self):
        text = []
        g = self.guess
        if 'episodeNumber' in g:
            text.append("Episode %s" % g['episodeNumber'])
        if 'title' in g:
            text.append(g['title'])
        text.append(self.get_extra_title())
        return " ".join(text)
    
    def get_season_title(self):
        text = []
        g = self.guess
        if 'series' in g:
            text.append(g['series'])
        if 'season' in g:
            text.append("Season %s" % g['season'])
        return " ".join(text)

    def get_full_title(self):
        title = [self.get_season_title(), self.get_episode_title()]
        return unicode(" ".join(title))
    
    def get_feature_title(self):
        return self.guess['series']
    
    def get_episode_name(self):
        return self.guess.get('title', '<none>')
    
    def is_playable(self):
        return True

def getDetail(guess):
    if guess['type'] == 'episode':
        return EpisodeDetail(guess)
    elif guess['type'] == 'movie':
        return MovieDetail(guess)
    else:
        return MediaDetail(guess['pathname'], str(guess))

def normalize_guess(guess):
    if guess['type'] == 'movie' and 'title' not in guess:
        title, _ = os.path.splitext(os.path.basename(filename))
        guess['title'] = unicode(title)

def guess_media_info(pathname):
    filename = normalize_filename(pathname)
    guess = guess_file_info(filename, "autodetect", info=['filename'])
    return guess

def guess_custom(pathname, regexps):
    filename, _ = os.path.splitext(pathname)
    for regexp in regexps:
        r = re.compile(regexp)
        match = r.match(filename)
        if match:
            metadata = match.groupdict()
            print metadata
            for prop, value in metadata.items():
                if prop in ('season', 'episodeNumber', 'year', 'extraNumber'):
                    if metadata[prop] is not None:
                        metadata[prop] = int(metadata[prop])
                if prop in ('title', 'extraTitle', 'series', 'filmSeries'):
                    if metadata[prop]:
                        metadata[prop] = utils.decode_title_text(metadata[prop])
                    else:
                        del metadata[prop]
            if 'season' in metadata:
                metadata['type'] = 'episode'
            else:
                metadata['type'] = 'movie'
            if 'filmSeries' in metadata:
                if 'title' not in metadata:
                    if 'episodeNumber' in metadata and metadata['episodeNumber'] > 1:
                        metadata['title'] = "%s %d" % (metadata['filmSeries'], metadata['episodeNumber'])
                    else:
                        metadata['title'] = metadata['filmSeries']
            guess = Guess(metadata, confidence = 1.0)
            print guess
            return guess
    return None

