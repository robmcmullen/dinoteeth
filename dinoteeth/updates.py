import os, time, logging

import pyinotify

from task import Task, ProcessTask, TaskManager, ThreadTaskDispatcher, ProcessTaskDispatcher
from download import BackgroundHttpDownloader

log = logging.getLogger("dinoteeth.updates")


class ThumbnailLoadTask(ProcessTask):
    def __init__(self, thumbnail_loader, imgpath):
        ProcessTask.__init__(self)
        self.thumbnail_loader = thumbnail_loader
        self.imgpath = imgpath
    
    def __str__(self):
        return "%s: thumbnail=%s" % (self.__class__.__name__, self.imgpath)
    
    def _start(self, dispatcher):
        self.thumbnail_loader.get_thumbnail_file(self.imgpath, True)
    
    def _success_message(self):
        return "Created thumbnail image for %s" % os.path.basename(self.imgpath)
    
    def _failed_message(self):
        return "Failed creating thumbnail image for %s" % os.path.basename(self.imgpath)

class UpdateManager(object):
    poster_thread = None
    
    def __init__(self, event_callback, db, thumbnail_loader):
        cls = self.__class__
        if cls.poster_thread is not None:
            raise RuntimeError("UpdateManager already initialized")
        cls.event_callback = event_callback
        cls.db = db
        cls.thumbnails = thumbnail_loader
        cls.task_manager = TaskManager(event_callback)
        dispatcher1 = ThreadTaskDispatcher()
        cls.task_manager.start_dispatcher(dispatcher1)
        dispatcher2 = ThreadTaskDispatcher(dispatcher1)
        cls.task_manager.start_dispatcher(dispatcher2)
        dispatcher3 = ProcessTaskDispatcher()
        cls.task_manager.start_dispatcher(dispatcher3)
        downloader = BackgroundHttpDownloader()
        cls.task_manager.start_dispatcher(downloader)
    
    @classmethod
    def process_tasks(cls):
        print "tasks!"
        tasks = cls.task_manager.get_finished()
        for task in tasks:
            print 'FINISHED:', str(task)
    
    @classmethod
    def create_thumbnail(cls, imgpath):
        task = ThumbnailLoadTask(cls.thumbnails, imgpath)
        cls.task_manager.add_task(task)
    
    @classmethod
    def test(cls, num=4, delay=.5):
        for i in range(num):
            task = TestSleepTask(i + 1, delay)
            cls.poster_thread.add_task(task)
    
    @classmethod
    def start_ticks(cls, delay, expire_time):
        cls.task_manager.start_ticks(delay, expire_time)
    
    @classmethod
    def stop_ticks(cls):
        cls.task_manager.stop_ticks()
    
    @classmethod
    def start_task(cls, task):
        cls.task_manager.add_task(task)
    
    @classmethod
    def stop_all(cls):
        cls.task_manager.shutdown()
        cls.process_tasks()


class FileWatcher(pyinotify.ProcessEvent):
    def __init__(self, db, pevent=None, **kwargs):
        pyinotify.ProcessEvent.__init__(self, pevent=pevent, **kwargs)
        self.db = db
        self.media_path_dict = {}
        self.wm = pyinotify.WatchManager() # Watch Manager
        self.added = set()
        self.removed = set()
    
    def add_path(self, path, flags):
        self.media_path_dict[path] = flags
    
    def watch(self):
        self.db.scan_and_update(self.media_path_dict)
        self.db.update_posters()
        mask = pyinotify.IN_DELETE | pyinotify.IN_CLOSE_WRITE | pyinotify.IN_MODIFY | pyinotify.IN_MOVED_TO | pyinotify.IN_MOVED_FROM | pyinotify.IN_CREATE
        notifier = pyinotify.Notifier(self.wm, self, timeout=5000)
        for path in self.media_path_dict.keys():
            self.wm.add_watch(path, mask, rec=True)
        while True:
            notifier.process_events()
            while notifier.check_events():  #loop in case more events appear while we are processing
                notifier.read_events()
                notifier.process_events()
            if len(self.added) + len(self.removed) > 0:
                print "Found %d files added, %d removed" % (len(self.added), len(self.removed))
                self.db.scan_and_update(self.media_path_dict)
                self.added = set()
                self.removed = set()
            else:
                print "no changes"
            self.db.update_posters()

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
