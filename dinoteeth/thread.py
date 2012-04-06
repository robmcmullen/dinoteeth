import os, time
from threading import Thread
import pyglet


class JobThread(Thread):
    def __init__(self, notify_window):
        Thread.__init__(self)
        self._notify_window = notify_window
        self._want_abort = False
        self.job_init()
        self.start()

    def run(self):
        pass

    def abort(self):
        # Method for use by main thread to signal an abort
        self._want_abort = 1


class TestStatusThread(JobThread):
    def job_init(self):
        self._count = 0
        
    def run(self):
        while True:
            time.sleep(0.2)
            print "Thread awake!"
            pyglet.app.platform_event_loop.post_event(self._notify_window, 'on_status_update', "Number %d" % self._count)
            self._count += 1
            if self._count % 5 == 0:
                time.sleep(3)
            if self._want_abort or self._count > 100:
                return
