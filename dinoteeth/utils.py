import os, sys, glob, urllib, logging, re, threading
from datetime import datetime, timedelta

from PIL import Image

log = logging.getLogger("dinoteeth.utils")

def decode_title_text(text):
    return text.replace('_n_',' & ').replace('-s_','\'s ').replace('-t_','\'t ').replace('-m_','\'m ').replace('.._',': ').replace('.,_','; ').replace('_',' ')

def encode_title_text(text):
    return text.replace(' & ','_n_').replace('\'s ','-s_').replace('\'t ','-t_').replace('\'m ','-m_').replace(': ','.._').replace('; ','.,_').replace(' ','_')

def shell_escape_path(path):
    escape_chars = [' ', '&', '(', ')']
    escaped_path = path
    for c in escape_chars: escaped_path = escaped_path.replace(c, "\\"+c)
    return escaped_path

def time_format(seconds):
    m, s = divmod(seconds, 60)
    h, m = divmod(m, 60)
    return "%d:%02d:%02d" % (h, m, s)

def time_since(d, now=None):
    """Fuzzy date printer, adapted from:
    
    http://jehiah.cz/a/printing-relative-dates-in-python
    http://stackoverflow.com/questions/11/how-do-i-calculate-relative-time
    """
    if not isinstance(d, datetime):
        d = datetime(d.year, d.month, d.day)
    if now and not isinstance(now, datetime):
        now = datetime(now.year, now.month, now.day)
    if not now:
        now = datetime.utcnow()
    delta = now - d
    minutes = delta.days * 24 * 60 + delta.seconds / 60
    
    if minutes < 0:
        return "not yet"
    if minutes < 1:
        return "just now"
    if minutes < 2:
        return "a minute ago"
    if minutes < 5:
        return "a few minutes ago"
    if minutes < 45:
        return "%d minutes ago" % int(minutes)
    if minutes < 90:
        return "an hour ago"
    
    hours = minutes / 60;
    if hours < 4:
        return "a few hours ago"
    if hours < 24:
        return "%d hours ago" % int(hours)
    
    midnight = datetime(now.year, now.month, now.day)
    hours_since_midnight = now - midnight
    days_since_midnight = delta - hours_since_midnight
    days = days_since_midnight.days + 1
    if days < 2:
        return "yesterday"
    if days < 7:
        return d.strftime("%A")
    if days < 31:
        return "%d days ago" % int(days)
    
    months = days / 30
    if months <= 1:
        return "one month ago"
    if months < 12:
        return "%d months ago" % months
    
    years = months / 12
    if years <= 1:
        return "one year ago"
    return "%d years ago" % years

def canonical_filename(title, film_series, season=-1, episode_char='e', episode=-1, episode_name='', ext="mkv"):
    name = []
    if season == -1:
        if film_series:
            name.append("%s-f%02d" % (film_series[0], int(film_series[1])))
        name.append(title)
    else:
        name.append(title)
        name.append("s%02d" % season)
    if episode > -1:
        name.append("%s%02d" % (episode_char, episode))
    if episode_name:
        name.append(episode_name)
    return encode_title_text("-".join(name) + ".%s" % ext)

class ArtworkLoader(object):
    lock = threading.Lock()
    
    def __init__(self, base_dir, default_poster, poster_width=-1, cache_size=100):
        self.base_dir = base_dir
        self.poster_dir = os.path.join(self.base_dir, "posters")
        self.thumbnail_dir = os.path.join(self.base_dir, "thumbnails")
        self.poster_width = poster_width
        if self.poster_width > 0:
            self.scaled_poster_dir = os.path.join(self.base_dir, "posters-scaled-width-%d" % poster_width)
        else:
            self.scaled_poster_dir = None
        self.use_cache = False
        self.cache = {}
        self.default_poster_path = default_poster
        self.default_poster = None
        self.check_dirs()
    
    def check_dirs(self):
        if not os.path.exists(self.base_dir):
            os.mkdir(self.base_dir)
        for dir in [self.poster_dir, self.thumbnail_dir, self.scaled_poster_dir]:
            if dir and not os.path.exists(dir):
                os.mkdir(dir)
    
    def get_default_poster(self):
        import pyglet
        if self.default_poster is None:
            self.default_poster = pyglet.image.load(self.default_poster_path)
        return self.default_poster
    
    def get_poster_basename(self, imdb_id, season=None, ext=".jpg"):
        if season is not None:
            basename = "%s-%s%s" % (imdb_id, season, ext)
        else:
            basename = "%s%s" % (imdb_id, ext)
        return basename
    
    def get_poster_filename(self, imdb_id, season=None):
        if imdb_id in self.cache:
            return self.cache[imdb_id][0]
        elif imdb_id is not None:
            basename = self.get_poster_basename(imdb_id, season)
            if self.scaled_poster_dir:
                filename = os.path.join(self.scaled_poster_dir, basename)
                if os.path.exists(filename):
                    return filename
            filename = os.path.join(self.poster_dir, basename)
            if os.path.exists(filename):
                return filename
        return None
    
    def has_poster(self, imdb_id, season=None):
        return self.get_poster_filename(imdb_id, season) is not None
    
    def save_poster_from_url(self, imdb_id, url, season=None):
        filename = url.split("/")[-1]
        (name, extension) = os.path.splitext(filename)
        basename = self.get_poster_basename(imdb_id, season, extension)
        pathname = os.path.join(self.poster_dir, basename)
        log.debug(pathname)
        if not os.path.exists(pathname) or os.stat(pathname)[6] == 0:
            log.debug("Downloading %s poster: %s" % (imdb_id, url))
            bytes = urllib.urlopen(url).read()
            with self.lock:
                fh = open(pathname, "wb")
                fh.write(bytes)
                fh.close()
            log.debug("Downloaded %s poster as %s" % (imdb_id, pathname))
            downloaded = True
        else:
            log.debug("Found %s poster: %s" % (imdb_id, pathname))
            downloaded = False
        # Check for existence of scaled poster
        if self.scaled_poster_dir:
            scaled_pathname = os.path.join(self.scaled_poster_dir, basename)
            if os.path.exists(scaled_pathname) and not downloaded:
                log.debug("Found %s scaled poster: %s" % (imdb_id, scaled_pathname))
                return
            img = Image.open(pathname)
            if img.size[0] <= self.poster_width:
                return
            with self.lock:
                height = img.size[1] * img.size[0] / self.poster_width
                size = (self.poster_width, height)
                img.thumbnail(size, Image.ANTIALIAS)
                img.save(scaled_pathname, "JPEG", quality=90)
            log.debug("Created %s scaled poster: %s" % (imdb_id, scaled_pathname))
    
    def get_poster(self, imdb_id, season=None):
        import pyglet
        key = (imdb_id, season)
        if key in self.cache:
            return self.cache[key][1]
        elif imdb_id is not None:
            filename = self.get_poster_filename(imdb_id, season)
            if filename is not None:
                with self.lock:
                    poster = pyglet.image.load(filename)
                if self.use_cache:
                    self.cache[key] = (filename, poster)
                return poster
        return self.get_default_poster()
    
    def get_image(self, imagepath):
        import pyglet
        if imagepath in self.cache:
            return self.cache[imagepath][1]
        filename = os.path.join(self.base_dir, imagepath)
        if os.path.exists(filename):
            with self.lock:
                image = pyglet.image.load(filename)
            if self.use_cache:
                self.cache[imagepath] = (filename, image)
            return image
        return self.get_default_poster()

def iter_dir(path, valid_extensions=None, exclude=None, verbose=False, recurse=False):
    if exclude is not None:
        try:
            exclude = re.compile(exclude)
        except:
            log.warning("Invalid regular expression %s" % exclude)
            pass
    videos = glob.glob(os.path.join(path, "*"))
    for video in videos:
        valid = False
        if os.path.isdir(video):
            if not video.endswith(".old"):
                if exclude:
                    match = cls.exclude.search(video)
                    if match:
                        log.debug("Skipping dir %s" % video)
                        continue
                log.debug("Checking dir %s" % video)
                if recurse:
                    iter_dir(video, valid_extensions, exclude, verbose, True)
        elif os.path.isfile(video):
            log.debug("Checking %s" % video)
            if valid_extensions:
                for ext in valid_extensions:
                    if video.endswith(ext):
                        valid = True
                        log.debug("Found valid media: %s" % video)
                        break
            else:
                valid = True
            if valid:
                yield video

if __name__ == "__main__":
    now = datetime(2012,4,3,12,34,56)
    print "Now: %s" % now.strftime("%A, %d %B %Y %I:%M%p")
    for d in [
        datetime(2012,4,3,1,23,45),
        datetime(2012,4,2,12,23,45),
        datetime(2012,4,2,1,23,45),
        datetime(2012,4,1,23,1,2),
        datetime(2012,4,1,1,23,45),
        datetime(2012,3,31,1,23,45),
        datetime(2012,3,30,1,23,45),
        datetime(2012,3,29,1,23,45),
        datetime(2012,3,28,1,23,45),
        datetime(2012,3,27,1,23,45),
        datetime(2012,3,12),
        datetime(2012,3,3),
        datetime(2012,2,12),
        datetime(2012,2,2),
        datetime(2012,1,12),
        datetime(2011,1,12),
        ]:
        print "%s: %s" % (d.strftime("%A, %d %B %Y %I:%M%p"), time_since(d, now))
