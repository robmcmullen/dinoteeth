import os, sys, glob
import pyglet

def decode_title_text(text):
    return text.replace('_n_',' & ').replace('-s_','\'s ').replace('-t_','\'t ').replace('-m_','\'m ').replace('.._',': ').replace('.,_','; ').replace('_',' ')

def shell_escape_path(path):
    escape_chars = [' ', '&', '(', ')']
    escaped_path = path
    for c in escape_chars: escaped_path = escaped_path.replace(c, "\\"+c)
    return escaped_path

def time_format(seconds):
    m, s = divmod(seconds, 60)
    h, m = divmod(m, 60)
    return "%d:%02d:%02d" % (h, m, s)

class ArtworkLoader(object):
    def __init__(self, base_dir, default_poster, cache_size=100):
        self.base_dir = base_dir
        self.poster_dir = os.path.join(self.base_dir, "posters")
        self.thumbnail_dir = os.path.join(self.base_dir, "thumbnails")
        self.cache = {}
        self.default_poster_path = default_poster
        self.default_poster = None
        self.check_dirs()
    
    def check_dirs(self):
        if not os.path.exists(self.base_dir):
            os.mkdir(self.base_dir)
        for dir in [self.poster_dir, self.thumbnail_dir]:
            if not os.path.exists(dir):
                os.mkdir(dir)
    
    def get_default_poster(self):
        if self.default_poster is None:
            self.default_poster = pyglet.image.load("graphics/artwork-not-available.png")
        return self.default_poster
    
    def get_poster(self, imdb_id):
        if imdb_id in self.cache:
            return self.cache[imdb_id]
        elif imdb_id is not None:
            filename = os.path.join(self.poster_dir, imdb_id + ".jpg")
            if os.path.exists(filename):
                poster = pyglet.image.load(filename)
                self.cache[imdb_id] = poster
                return poster
        return self.get_default_poster()
    
    def get_image(self, imagepath):
        if imagepath in self.cache:
            return self.cache[imagepath]
        filename = os.path.join(self.base_dir, imagepath)
        if os.path.exists(filename):
            image = pyglet.image.load(filename)
            self.cache[imagepath] = image
            return image
        return self.get_default_poster()
