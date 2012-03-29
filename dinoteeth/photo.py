import os, sys, re, bisect, glob, subprocess

import utils


class PhotoDir(object):
    valid_image_types = ['.jpg', '.png']
    
    def __init__(self, path):
        self.path = path
        self.in_context_title = os.path.basename(self.path)
        self.pics = None
    
    def __str__(self):
        return self.path
    
    def get_pics(self):
        if self.pics is not None:
            return self.pics
        self.pics = []
        images = glob.glob(os.path.join(self.path, "*"))
        images.sort()
        for image in images:
            if not os.path.isdir(image):
                _, ext = os.path.splitext(image)
                if ext.lower() in self.valid_image_types:
                    self.pics.append(image)
        return self.pics
    
    def iter_pics(self):
        pics = self.get_pics()
        for pic in pics:
            yield pic

    # MenuItem methods
    
    def add_to_menu(self, theme, parent_menu):
        menu, handled = theme.add_simple_menu(self, parent_menu)
        menu.metadata = {'imagegen': self.thumbnail_mosaic}
        menu.action = self.slideshow
        return menu, True
    
    def slideshow(self, config=None):
        config.prepare_for_external_app()
        print "Starting slideshow for %s" % self.path
        args = [sys.executable, "bin/slideshow.py", "--once", self.path]
        p = subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        output, errors = p.communicate()
        print output
        print errors
        config.restore_after_external_app()

    def thumbnail_mosaic(self, artwork_loader, thumbnail_factory, x, y, w, h):
        min_x = x
        max_x = x + w
        min_y = y
        y = y + h
        nominal_x = 130
        nominal_y = 130
        for imgpath in self.iter_pics():
            try:
                thumb_image = thumbnail_factory.get_image(imgpath)
            except:
                print "skipping bad image: %s" % imgpath
                continue
            print thumb_image.width, thumb_image.height
            if x + nominal_x > max_x:
                x = min_x
                y -= nominal_y
            if y < min_y:
                break
            thumb_image.blit(x + (nominal_x - thumb_image.width) / 2, y - nominal_y + (nominal_y - thumb_image.height) / 2, 0)
            x += nominal_x

class PhotoDB(object):
    def __init__(self):
        self.paths = []
        self.children = []
    
    def add_path(self, path):
        self.paths.append(path)
    
    def hierarchy(self):
        dirs = []
        for path in self.paths:
            dirs.extend(glob.glob(os.path.join(path, "*")))
        dirs.sort()
        for dir in dirs:
            if os.path.isdir(dir):
                self.children.append(PhotoDir(dir))
        print self.children
        return self
