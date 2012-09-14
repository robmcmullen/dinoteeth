import os, time, logging

import pyinotify

from thread2 import ThreadTaskManager, ProcessTaskManager, TestSleepTask

log = logging.getLogger("dinoteeth.updates")


class ThumbnailLoadTask(object):
    def __init__(self, imgpath):
        self.imgpath = imgpath
    
    def __str__(self):
        return "%s: thumbnail=%s" % (self.__class__.__name__, self.imgpath)
    
    def __call__(self, thumbnails=None, *args, **kwargs):
        try:
            thumbnails.get_thumbnail_file(self.imgpath, True)
            return "Created thumbnail image for %s" % os.path.basename(self.imgpath)
        except:
            return "Failed creating thumbnail image for %s" % os.path.basename(self.imgpath)

class TimerTask(object):
    def __init__(self, delay, expire_time, repeat=True):
        self.delay = delay
        self.expire_time = expire_time
        self.repeat = repeat
    
    def __call__(self, *args, **kwargs):
        time.sleep(self.delay)
        if time.time() >= self.expire_time:
            self.repeat = False


class UpdateManager(object):
    poster_thread = None
    
    def __init__(self, window, event_name, db, thumbnail_loader):
        cls = self.__class__
        if cls.poster_thread is not None:
            raise RuntimeError("UpdateManager already initialized")
        cls.window = window
        cls.event_name = event_name
        cls.db = db
        cls.thumbnails = thumbnail_loader
        cls.poster_thread = ProcessTaskManager(window, event_name, num_workers=1, thumbnails=cls.thumbnails)
        cls.timer_thread = ThreadTaskManager(window, 'on_timer')
    
    @classmethod
    def create_thumbnail(cls, imgpath):
        task = ThumbnailLoadTask(imgpath)
        cls.poster_thread.add_task(task)
    
    @classmethod
    def test(cls, num=4, delay=.5):
        for i in range(num):
            task = TestSleepTask(i + 1, delay)
            cls.poster_thread.add_task(task)
    
    @classmethod
    def start_ticks(cls, delay, expire_time):
        task = TimerTask(delay, expire_time)
        cls.timer_thread.add_task(task)
    
    @classmethod
    def stop_ticks(cls):
        task = TimerTask(0, 0, repeat=False)
        cls.timer_thread.add_task(task)
    
    @classmethod
    def stop_all(cls):
        ProcessTaskManager.stop_all()


class FileWatcher(pyinotify.ProcessEvent):
    def __init__(self, db, valid_extensions, poster_loader, pevent=None, **kwargs):
        pyinotify.ProcessEvent.__init__(self, pevent=pevent, **kwargs)
        self.db = db
        self.extensions = valid_extensions
        self.poster_loader = poster_loader
        self.media_path_dict = {}
        self.wm = pyinotify.WatchManager() # Watch Manager
        self.added = set()
        self.removed = set()
    
    def add_path(self, path, flags):
        self.media_path_dict[path] = flags
    
    def watch(self):
        self.db.update_metadata(self.media_path_dict, self.extensions)
        self.db.update_posters(self.poster_loader)
        mask = pyinotify.IN_DELETE | pyinotify.IN_CLOSE_WRITE | pyinotify.IN_MODIFY | pyinotify.IN_MOVED_TO | pyinotify.IN_MOVED_FROM | pyinotify.IN_CREATE
        notifier = pyinotify.Notifier(self.wm, self, timeout=1000)
        for path in self.media_path_dict.keys():
            self.wm.add_watch(path, mask, rec=True)
        while True:
            notifier.process_events()
            while notifier.check_events():  #loop in case more events appear while we are processing
                notifier.read_events()
                notifier.process_events()
            if len(self.added) + len(self.removed) > 0:
                print "Found %d files added, %d removed" % (len(self.added), len(self.removed))
                self.db.update_metadata(self.media_path_dict, self.extensions)
                self.db.update_posters(self.poster_loader)
                self.added = set()
                self.removed = set()
            else:
                print "no changes"

    def process_IN_CLOSE_WRITE(self, event):
#        print "Modified (closed):", event.pathname
        self.added.add(event.pathname)

    def process_IN_DELETE(self, event):
#        print "Removed (deleted):", event.pathname
        self.removed.add(event.pathname)

    def process_IN_MODIFY(self, event):
#        print "Modified:", event.pathname
        self.added.add(event.pathname)

    def process_IN_MOVED_TO(self, event):
#        print "Modified (moved to):", event.pathname
        self.added.add(event.pathname)

    def process_IN_MOVED_FROM(self, event):
#        print "Removed (moved from):", event.pathname
        self.removed.add(event.pathname)

    def process_IN_CREATE(self, event):
#        print "Removed (deleted):", event.pathname
        self.added.add(event.pathname)
