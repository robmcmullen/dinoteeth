import os, sys, glob, re
import pyglet

from model import MenuDetail
import utils

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
        return True


class MovieTitle(object):
    """Class to hold a movie title broken up by its components
    
    """
    regex = re.compile(r"(.+)(([-_][sS]([0-9]+))?([-_][dD]([0-9]+))?([-_][eE]([0-9]+))?)")
    regex = re.compile(r"([_A-Za-z0-9]+)([-_][eE]?([0-9]+))?")
    #regex = re.compile(r"(.+)([-_][eE]([0-9]+))$")
    regex = {
        'season': re.compile(r"([-_](?:s|season?)([0-9]+))([-_]|$)", re.IGNORECASE),
        'episode': re.compile(r"([-_]e([0-9]+))([-_]|$)", re.IGNORECASE),
        'extra': re.compile(r"([-_](?:x|extra_?)([0-9]+))([-_]|$)", re.IGNORECASE),
        'disc': re.compile(r"([-_](?:d|disc)([0-9]+))([-_]|$)", re.IGNORECASE),
        'angle': re.compile(r"([-_]angle([0-9]+))([-_]|$)", re.IGNORECASE),
        'seasonepisode': re.compile(r"([-_]s([0-9]+)e([0-9]+))([-_]|$)", re.IGNORECASE),
        'crop': re.compile(r"([-_](crop=[0-9:]+))([-_]|$)", re.IGNORECASE),
        'aspect': re.compile(r"([-_]aspect=([0-9:]+))([-_]|$)", re.IGNORECASE),
        'episodename': re.compile(r"([-_](gag[-_]reel|(?:[a-z]+[-_])*featurette))([-_]|$)", re.IGNORECASE),
        }
    
    def __init__(self, filename, extra_text=""):
        self.verbose = 0
        
        self.pathname = ""
        self.title = ""
        self.season = -1
        self.disc = -1
        self.episode = -1
        self.extra = -1
        self.angle = -1
        self.episode_name = ""
        self.crop = ""
        self.aspect = ""
        self.extra_text = extra_text
        
        self.first_metadata_pos = -1
        self.parseFilename(filename)
    
    def __cmp__(self, other):
        return cmp((self.sortKey(), self.season, self.disc, self.extra, self.episode, self.angle, self.extra, self.episode_name),
                   (other.sortKey(), other.season, other.disc, other.extra, other.episode, other.angle, other.episode_name))
    
    def sortKey(self):
        title = self.title.lower()
        if title.startswith("the "):
            title = title[4:]
        if title.startswith("a "):
            title = title[2:]
        return title
    
    def __str__(self):
        lines = ["%s" % self.title]
        if self.season > 0:
            lines.append("Season %d" % self.season)
        if self.disc > 0:
            lines.append("Disc %d" % self.disc)
        if self.episode > 0:
            lines.append("Episode %d" % self.episode)
        if self.extra > 0:
            lines.append("Bonus Feature %d" % self.extra)
        if self.angle > 0:
            lines.append("Angle %d" % self.angle)
        if self.episode_name:
            lines.append("%s" % self.episode_name)
        if self.extra_text:
            lines.append("%s" % self.extra_text)
        return " ".join(lines)
    
    def isPath(self, path):
        return path == self.pathname
    
    def parseFilename(self, filename):
        self.pathname = filename
        root, ext = os.path.splitext(filename)
        basename = os.path.basename(root)
        self.first_metadata_pos = len(basename)
        for scan in ['season', 'episode', 'extra', 'disc', 'angle']:
            basename = self.parseRegex(basename, scan)
        basename = self.parseSpecial(basename)
        basename = self.parseMPlayer(basename)
        basename = self.parseEpisodeName(basename)
        self.parseTitle(basename)
    
    def parseTitle(self, basename):
        title = utils.decode_title_text(basename)
        if title.startswith("Top Gear"):
            self.episode_name += title[8:].strip()
            title = "TopGear"
        self.title = title
    
    def parseRegex(self, basename, scan):
        regex = self.regex[scan]
        match = regex.search(basename)
        if match:
            setattr(self, scan, int(match.group(2)))
            basename = basename[0:match.start(1)] + basename[match.end(1):]
            if match.start(1) < self.first_metadata_pos:
                self.first_metadata_pos = match.start(1)
            if self.verbose > 0: print("name=%s %s=%s" % (basename, scan, getattr(self, scan)))
        return basename
    
    def parseSpecial(self, basename):
        regex = self.regex['seasonepisode']
        match = regex.search(basename)
        if match:
            self.season = int(match.group(2))
            self.episode = int(match.group(3))
            basename = basename[0:match.start(1)] + basename[match.end(1):]
            if match.start(1) < self.first_metadata_pos:
                self.first_metadata_pos = match.start(1)
            if self.verbose > 0: print("name=%s season=%d episode=%d" % (basename, self.season, self.episode))
        return basename
    
    def parseMPlayer(self, basename):
        regex = self.regex['crop']
        match = regex.search(basename)
        if match:
            self.crop = match.group(2)
            basename = basename[0:match.start(1)] + basename[match.end(1):]
            if match.start(1) < self.first_metadata_pos:
                self.first_metadata_pos = match.start(1)
            if self.verbose > 0: print("name=%s crop=%s" % (basename, self.crop))
        regex = self.regex['aspect']
        match = regex.search(basename)
        if match:
            self.aspect = match.group(2)
            basename = basename[0:match.start(1)] + basename[match.end(1):]
            if match.start(1) < self.first_metadata_pos:
                self.first_metadata_pos = match.start(1)
            if self.verbose > 0: print("name=%s aspect=%s" % (basename, self.aspect))
        return basename
    
    def addMPlayerOpts(self, opts):
        if self.crop:
            opts.extend(["-vf", self.crop])
        if self.aspect:
            opts.extend(["-aspect", self.aspect])
    
    def parseEpisodeName(self, basename):
        regex = self.regex['episodename']
        match = regex.search(basename)
        if match:
            if match.start(1) < self.first_metadata_pos:
                self.first_metadata_pos = match.start(1)
        self.episode_name = utils.decode_title_text(basename[self.first_metadata_pos:].strip().strip("_").strip("-").strip())
        return basename[0:self.first_metadata_pos]
