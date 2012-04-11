#!/usr/bin/env python
"""Simple pyglet slideshow application

Takes list of image files and displays each in order with a delay between
each transition.
"""
import os, sys, glob, time, logging, threading, Queue
from optparse import OptionParser
from cStringIO import StringIO

import pyglet
from pyglet.gl import *
import pyglet.image
from PIL import Image, PngImagePlugin

log = logging.getLogger("slideshow")
log.setLevel(logging.DEBUG)
log.addHandler(logging.StreamHandler())
threadlog = logging.getLogger("slideshow.thread")
threadlog.setLevel(logging.DEBUG)

class ImageAccess(object):
    lock = threading.Lock()
    log = logging.getLogger("slideshow.image")

#    @classmethod
#    def get_image_handle(cls, filename, size):
#        fh = None
##        with cls.lock:
#        if True:
#            try:
#                img = Image.open(filename)
#                orientation = 1
#                if hasattr(img, '_getexif'):
#                    try:
#                        exif = img._getexif()
#                        if exif != None and 0x0112 in exif:
#                            orientation = exif[0x0112]
#                    except:
#                        pass
#                if orientation == 6:
#                    img = img.transpose(Image.ROTATE_270)
#                elif orientation == 3:
#                    img = img.transpose(Image.ROTATE_180)
#                elif orientation == 8:
#                    img = img.transpose(Image.ROTATE_90)
#                img.thumbnail(size, Image.ANTIALIAS)
#                fh = StringIO()
#                img.save(fh, format="JPEG")
#                fh.seek(0)
#            except Exception, e:
#                cls.log.error("Error loading %s: %s" % (filename, e))
#        return fh
#    
#    @classmethod
#    def pyglet_from_image_handle(cls, filename, fh):
#        first_exception = None
#        fh.seek(0)
##        with cls.lock:
#        if True:
#            image = None
#            for decoder in pyglet.image.codecs.get_decoders(filename):
#                try:
#                    image = decoder.decode(fh, filename)
#                    break
#                except pyglet.image.codecs.ImageDecodeException, e:
#                    if (not first_exception or 
#                        first_exception.exception_priority < e.exception_priority):
#                        first_exception = e
#                    file.seek(0)
#        
#        if image is not None:
#            return image
#
#        if not first_exception:
#            raise pyglet.image.codecs.ImageDecodeException('No image decoders are available')
#        raise first_exception
    
    @classmethod
    def get_image_handle(cls, filename, size):
        fh = None
#        with cls.lock:
        if True:
            try:
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
                #img.thumbnail(size, Image.ANTIALIAS)
                #img.thumbnail(size, Image.BICUBIC)
                img.thumbnail(size, Image.BILINEAR)
                #img.thumbnail(size, Image.NEAREST)
                
                img = img.transpose(Image.FLIP_TOP_BOTTOM)

                # Convert bitmap and palette images to component
                if img.mode in ('1', 'P'):
                    img = img.convert()

                if img.mode not in ('L', 'LA', 'RGB', 'RGBA'):
                    raise ImageDecodeException('Unsupported mode "%s"' % img.mode)
                type = GL_UNSIGNED_BYTE
                width, height = img.size

                fh = pyglet.image.ImageData(width, height, img.mode, img.tostring())
                print fh
            except Exception, e:
                cls.log.error("Error loading %s: %s" % (filename, e))
        return fh
    
    @classmethod
    def pyglet_from_image_handle(cls, filename, fh):
        if fh is None:
            raise RuntimeError("Bad image: %s" % filename)
        return fh
    
    @classmethod
    def blit(cls, image, x, y):
#        with cls.lock:
#            image.blit(x, y)
        image.blit(x, y)


class CommandQueue(threading.Thread):
    def __init__(self, notify_window, ready_event, status_event, paths, size, *args, **kwargs):
        threading.Thread.__init__(self)
        self._notify_window = notify_window
        self._ready_event = ready_event
        self._status_event = status_event
        self._want_abort = False
        self._command_queue = Queue.Queue()
        self._status_text = Queue.Queue()
        self._image_order = paths
        self._unique_images = set(paths)
        self._num_unique = len(self._unique_images)
        self._good_images = set()
        self._bad_images = set()
        self._index = 0
        self._ready = {}
        self._loaded_all = False
        self._size = size
        self.setDaemon(True)
        self.start()
    
    def _next_command(self, block=False):
        try:
            entry = self._command_queue.get(block)
            return entry[0], entry[1:]
        except Queue.Empty:
            return None, None

    def put_command(self, *args):
        self._command_queue.put(args)
        
    def _status_update(self, *args, **kwargs):
        self._status_text.put(args[0])
        pyglet.app.platform_event_loop.post_event(self._notify_window, self._status_event, *args, **kwargs)

    def run(self):
        block = False
        last_get = None
        while True:
            threadlog.debug("waiting for command (block=%s)..." % block)
            next, args = self._next_command(block)
            threadlog.debug("found command: %s" % next)
            if next == "get":
                filename = args[0]
                last_get = filename
                
                # pull off all the consecutive get requests to make sure the
                # user doesn't queue up a bunch of requests that overburden
                # the request queue
                if not block:
                    threadlog.debug("checking for stacked get requests after this one: %s" % filename)
                    continue
            if last_get:
                threadlog.debug("processing get request: %s" % filename)
                if filename not in self._ready:
                    self._load(filename)
                fh = self._ready[filename]
                if hasattr(fh, 'seek'):
                    fh.seek(0)
                pyglet.app.platform_event_loop.post_event(self._notify_window, self._ready_event, filename, fh)
                last_get = None
            elif next == "abort":
                return
            elif next == "size":
                self._size = args[0]
                self._ready = {}
                self._good_images = set()
                self._loaded_all = False
            elif next is not None:
                threadlog.debug("Unknown command: %s" % next)
            block = self._work_item()

    def abort(self):
        # Method for use by main thread to signal an abort
        self._command_queue.put("abort")
        self._want_abort = True
    
    def _work_item(self):
        if self._loaded_all:
            return True
        filename = self._image_order[self._index]
        if filename not in self._bad_images and filename not in self._good_images:
            threadlog.debug("Processing work item %d: %s" % (self._index, filename))
            self._load(filename)
        self._index += 1
        if self._index == len(self._image_order):
            self._index = 0
        if len(self._good_images) + len(self._bad_images) == self._num_unique:
            threadlog.debug("Reached end of work item queue")
            self._status_update("Reached end of work item queue")
            self._loaded_all = True
        return False

    def _load(self, filename):
        """Resulting image will be rotated according to EXIF data.
        
        http://www.impulseadventure.com/photo/exif-orientation.html
        """
        threadlog.debug("loading file %s" % filename)
        self._status_update("loading file %s" % os.path.basename(filename))
        fh = ImageAccess.get_image_handle(filename, self._size)
        if fh is None:
            threadlog.debug("Error loading file %s" % filename)
            self._bad_images.add(filename)
        else:
            self._good_images.add(filename)
        self._ready[filename] = fh

class Slideshow(pyglet.window.Window):
    def __init__(self, image_filenames, time, fullscreen=False, width=1600, height=900, margins=None, once=False):
        if fullscreen:
            super(Slideshow, self).__init__(fullscreen=fullscreen)
        else:
            super(Slideshow, self).__init__(width, height)
        if margins is None:
            margins = (0, 0, 0, 0)
        self.paths = image_filenames
        self.current = None
        self.bad_image = 0
        self.index = -1
        self.request = -1
        self.request_delta = 1
        self.interval = time
        self.once = once
        
        glEnable(GL_BLEND)
        glShadeModel(GL_SMOOTH)
        glBlendFunc(GL_SRC_ALPHA, GL_ONE)
        glDisable(GL_DEPTH_TEST)
        
        self.status_renderer = SimpleStatusRenderer(self)
        self.thread = CommandQueue(self, 'on_image_ready', 'on_status_change', self.paths, self.get_size())
        self.transition(None)
    
    def transition(self, dt, delta=1):
        log.debug("next slide")
        self.request_delta = delta
        self.request = self.next_request()
        try:
            filename = self.paths[self.request]
        except IndexError:
            # reached end; quit
            sys.exit()
        
        log.debug("Requesting display of: %s" % filename)
        self.thread.put_command("get", filename)
    
    def next_request(self):
        index = self.request + self.request_delta
        if index >= len(self.paths):
            if self.once:
                index = len(self.paths)
            else:
                index = 0
        elif index < 0:
            index = 0
        return index
    
    def force_transition(self, delta=1):
        pyglet.clock.unschedule(self.transition)
        self.transition(None, delta)
    
    def on_draw(self):
        log.debug("draw")
        self.clear()
        if self.current is not None:
            x, y, w, h = self.calc_size(self.current)
            #self.current.blit(x, y, width=w, height=h)
            #self.current.blit(x, y)
            ImageAccess.blit(self.current, x, y)
            w, h = self.get_size()
            text = "%d/%d %s" % (self.index + 1, len(self.paths), os.path.basename(self.paths[self.index]))
            label = pyglet.text.Label(text,
                                      font_name="Arial",
                                      font_size=16,
                                      bold=False, italic=False, color=(0,255,0,192),
                                      x=10, y=h - 10,
                                      anchor_x='left', anchor_y='top')
            label.draw()
        self.status_renderer.draw()
    
    def calc_size(self, image):
        w, h = self.get_size()
        x, y = image.width, image.height
        if x > w: y = max(y * w / x, 1); x = w
        if y > h: x = max(x * h / y, 1); y = h
        xoff = (w - x) / 2
        yoff = (h - y) / 2
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
            self.thread.put_command("size", self.get_size())
            self.force_transition(0)
    
    def on_image_ready(self, filename, fh):
        log.debug("Thread loaded %s" % filename)
        try:
            self.current = ImageAccess.pyglet_from_image_handle(filename, fh)
            self.index = self.request
            self.request_delta = 1
            self.bad_image = 0
            pyglet.clock.schedule_once(self.transition, self.interval)
        except Exception, e:
            # Bad image!  Skip to next image in the desired direction
            log.error("bad image: %s\n****  %s" % (filename, e))
            self.bad_image += 1
            if self.bad_image == len(self.paths):
                log.error("All images are bad!  Exiting")
                sys.exit()
            # Continue in the same direction
            delta = self.request_delta
            if delta < 0:
                delta = -1
            else:
                delta = 1
            self.transition(self.interval, delta)

    def on_status_change(self, *args):
        print "clearing status bar"
        self.flip()
        
Slideshow.register_event_type('on_image_ready')
Slideshow.register_event_type('on_status_change')

class SimpleStatusRenderer(object):
    def __init__(self, window):
        self.window = window
        self.width, self.height = self.window.get_size()
        self.x = 10
        self.y = 10
        self.w = self.width - 20
        self.h = 30
        self.last_item = None
        self.expire_time = time.time() + 10
        self.display_interval = 5
    
    def draw(self):
        found = False
        while True:
            try:
                # Pull as many status updates off the queue as there are; only
                # display the most recent update
                item = self.window.thread._status_text.get(False)
                found = True
                self.last_item = item
            except Queue.Empty:
                break
        if found:
            # New item found means resetting the countdown timer back to the
            # maximum
            self.expire_time = time.time() + self.display_interval
            pyglet.clock.unschedule(self.window.on_status_change)
            pyglet.clock.schedule_once(self.window.on_status_change, self.display_interval)
        else:
            # No items found means that the countdown timer is left as-is
            print "no status available"
            if self.last_item is None:
                return
            
        if time.time() > self.expire_time:
            # If the countdown timer has expired, no drawing takes place
            pyglet.clock.unschedule(self.window.on_status_change)
            return
        print "status drawing! (%d,%d) %s" % (self.x, self.y, self.last_item)
        verts = (
            self.x + self.w, self.y + self.h,
            self.x, self.y + self.h,
            self.x, self.y,
            self.x + self.w, self.y
        )
        colors = (
            255, 255, 255, 128,
            255, 255, 255, 128,
            255, 255, 255, 128,
            255, 255, 255, 128,
        )
        pyglet.graphics.draw(4, GL_QUADS, ('v2i', verts), ('c4B', colors))
        colors = (
            255, 255, 255, 255,
            255, 255, 255, 255,
            255, 255, 255, 255,
            255, 255, 255, 255,
        )
        pyglet.graphics.draw(4, GL_LINE_LOOP, ('v2i', verts), ('c4B', colors))
        label = pyglet.text.Label(self.last_item,
                                  font_name="Arial",
                                  font_size=20,
                                  bold=True, italic=True, color=(255,0,0,255),
                                  x=self.x + 10, y=self.y + (self.h / 2),
                                  anchor_x='left', anchor_y='center')
        label.draw()

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
