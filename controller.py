import os, sys, glob
import pyglet

from mplayer import MplayerTarget


class Menu(object):
    def __init__(self, config):
        self.config = config
        self.cursor = 0
    
    def get_label(self, index):
        return "Entry #%d" % index
    
    def get_detail_image(self, index):
        return self.config.get_default_poster()
    
    def get_details(self, index):
        return "Details for entry #%d" % index
    
    def num_labels(self):
        return 50

    def process_motion(self, motion, layout):
        print "here"
        if motion == pyglet.window.key.MOTION_UP:
            self.cursor -= 1
        elif motion == pyglet.window.key.MOTION_PREVIOUS_PAGE:
            self.cursor -= layout.menu_renderer.get_page_scroll_unit()
        elif motion == pyglet.window.key.MOTION_DOWN:
            self.cursor += 1
        elif motion == pyglet.window.key.MOTION_NEXT_PAGE:
            self.cursor += layout.menu_renderer.get_page_scroll_unit()
        if self.cursor < 0:
            self.cursor = 0
        elif self.cursor >= self.num_labels():
            self.cursor = self.num_labels() - 1


class MovieMenu(Menu):
    video_extensions = ['.vob', '.mp4', '.avi', '.wmv', '.mov', '.mpg', '.mpeg', '.mpeg4', '.mkv', '.flv']
    
    def __init__(self, config, path):
        super(MovieMenu, self).__init__(config)
        self.videos = []
        self.add_videos_in_path(path)
        
    def add_videos_in_path(self, dir):
        videos = glob.glob(os.path.join(dir, "*"))
        for video in videos:
            valid = False
            if os.path.isdir(video):
                if not video.endswith(".old"):
                    if self.exclude:
                        match = self.exclude.search(video)
                        if match:
                            if self.verbose: print("Skipping dir %s" % video)
                            continue
                    print("Checking dir %s" % video)
                    self.add_videos_in_path(video)
            elif os.path.isfile(video):
                print("Checking %s" % video)
                for ext in self.video_extensions:
                    if video.endswith(ext):
                        valid = True
                        print ("Found valid media: %s" % video)
                        break
                if valid:
                    self.add_video(video)
        self.videos.sort()
    
    def add_video(self, filename):
        """Check to see if the filename is associated with a series
        """
        video = MplayerTarget(self.config, filename)
        self.videos.append(video)

    def get_label(self, index):
        video = self.videos[index]
        return video.title
    
    def get_detail_image(self, index):
        video = self.videos[index]
        return video.get_image()
    
    def get_details(self, index):
        video = self.videos[index]
        return video.details
    
    def num_labels(self):
        return len(self.videos)
