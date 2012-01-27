#!/usr/bin/env python
"""Simple pyglet slideshow application

Takes list of image files and displays each in order with a delay between
each transition.
"""
import os, sys, glob
from optparse import OptionParser
from cStringIO import StringIO

import pyglet
from PIL import Image, PngImagePlugin

class Slideshow(pyglet.window.Window):
    def __init__(self, image_filenames, time, fullscreen=False, width=800, height=600, margins=None, verbose=False, once=False):
        if fullscreen:
            super(Slideshow, self).__init__(fullscreen=fullscreen)
        else:
            super(Slideshow, self).__init__(width, height)
        if margins is None:
            margins = (0, 0, 0, 0)
        self.paths = image_filenames
        self.current = None
        self.index = -1
        self.interval = time
        self.verbose = verbose
        self.once = once
        self.transition(None)
    
    def transition(self, dt, delta=1):
        if self.verbose: print "next slide"
        self.index = self.calc_index(delta)
        try:
            filename = self.paths[self.index]
        except IndexError:
            # reached end; quit
            sys.exit()
        if self.verbose: print "loading %s" % filename
        try:
            self.current = self.get_image(filename)
            pyglet.clock.schedule_once(self.transition, self.interval)
        except:
            # Bad image!  Skip to next image in the desired direction
            print "bad image: %s" % filename
            if delta < 0:
                delta = -1
            else:
                delta = 1
            next_index = self.calc_index(delta)
            if next_index != self.index:
                self.transition(self.interval, delta)
            else:
                sys.exit()
    
    def calc_index(self, delta):
        index = self.index + delta
        if index >= len(self.paths):
            if self.once:
                index = len(self.paths)
            else:
                index = 0
        elif index < 0:
            index = 0
        return index
    
    def get_image(self, filename):
        """If image is rotated according to EXIF data, rotate the thumbnail
        before returning.
        
        http://www.impulseadventure.com/photo/exif-orientation.html
        """
        img = Image.open(filename)
        orientation = 1
        if hasattr(img, '_getexif'):
            try:
                exif = img._getexif()
                if exif != None and 0x0112 in exif:
                    orientation = exif[0x0112]
            except:
                pass
        
        if orientation == 6:
            img = img.transpose(Image.ROTATE_270)
        elif orientation == 3:
            img = img.transpose(Image.ROTATE_180)
        elif orientation == 8:
            img = img.transpose(Image.ROTATE_90)
            
        img.thumbnail(self.get_size(), Image.ANTIALIAS)
        
        fh = StringIO()
        img.save(fh, format="JPEG")
        fh.seek(0)
        
        img = pyglet.image.load(filename, fh)
        return img
    
    def force_transition(self, delta=1):
        pyglet.clock.unschedule(self.transition)
        self.transition(None, delta)
    
    def on_draw(self):
        if self.verbose: print "draw"
        self.clear()
        if self.current is not None:
            x, y, w, h = self.calc_size(self.current)
            #self.current.blit(x, y, width=w, height=h)
            self.current.blit(x, y)
    
    def calc_size(self, image):
        size = self.get_size()
        x, y = image.width, image.height
        if x > size[0]: y = max(y * size[0] / x, 1); x = size[0]
        if y > size[1]: x = max(x * size[1] / y, 1); y = size[1]
        xoff = (size[0] - x) / 2
        yoff = (size[1] - y) / 2
        return xoff, yoff, x, y
    
    def on_text_motion(self, motion):
        k = pyglet.window.key
        
        delta = 0
        if motion == k.MOTION_UP or motion == k.MOTION_RIGHT:
            delta = 1
        elif motion == k.MOTION_DOWN or motion == k.MOTION_LEFT:
            delta = -1
        elif motion == k.MOTION_BEGINNING_OF_LINE or motion == k.MOTION_BEGINNING_OF_FILE:
            delta = -1000000
        elif motion == k.MOTION_END_OF_LINE or motion == k.MOTION_END_OF_FILE:
            delta = 1000000
        self.force_transition(delta)

    def on_key_press(self, symbol, modifiers):
        k = pyglet.window.key
        if symbol == k.Q or symbol == k.ESCAPE:
            pyglet.app.exit()
        elif symbol == k.F:
            self.set_fullscreen(not self.fullscreen)
            self.force_transition(0)

def add_images(dir, images):
    files = glob.glob(os.path.join(dir, "*"))
    sub_images = []
    for file in files:
        if os.path.isdir(file):
            add_images(file, images)
        sub_images.append(file)
    sub_images.sort()
    images.extend(sub_images)

if __name__ == "__main__":
    usage="usage: %prog [options] [files...]\n\n" + __doc__
    parser=OptionParser(usage=usage)
    parser.add_option("-v", action="store_true", dest="verbose", default=False,
                      help="display verbose status messages")
    parser.add_option("-f", action="store", dest="from_file", default=None,
                      help="load image filenames from this file")
    parser.add_option("-t", action="store", type="int", dest="time", default=6,
                      help="delay (in seconds) before transitioning to next image")
    parser.add_option("-w", "--window", action="store_false", dest="fullscreen", default=True)
    parser.add_option("--once", action="store_true", dest="once", default=False,
                      help="only display the set of images once and quit after the last image")
    (options, args) = parser.parse_args()

    images = []
    if options.from_file:
        fh = open(options.from_file)
        for line in fh.readlines():
            path = line.strip()
            if path:
                images.append(path)
    
    for name in args:
        if os.path.isdir(name):
            add_images(name, images)
        else:
            images.append(name)
    window = Slideshow(images, options.time, fullscreen=options.fullscreen, once=options.once)
    pyglet.app.run()