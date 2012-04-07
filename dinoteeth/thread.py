import os, time, logging, threading, Queue
import pyglet

log = logging.getLogger("dinoteeth.thread")


class PygletTask(threading.Thread):
    def __init__(self, notify_window, notify_event, *args, **kwargs):
        threading.Thread.__init__(self)
        self._notify_window = notify_window
        self._notify_event = notify_event
        self.init_hook()
        self.task_setup(*args, **kwargs)
        self.start()
    
    def init_hook(self):
        self._want_abort = False

    def run(self):
        self.task()
    
    def notify(self, *args, **kwargs):
        """Called from within the thread"""
        pyglet.app.platform_event_loop.post_event(self._notify_window, self._notify_event, *args, **kwargs)

    def abort(self):
        # Method for use by main thread to signal an abort
        self._want_abort = True

class PygletCommandQueue(PygletTask):
    def init_hook(self):
        PygletTask.init_hook(self)
        self.setDaemon(True)
        self._command_queue = Queue.Queue()
    
    def _next_command(self):
        return self._command_queue.get() # Blocking

    def put_command(self, cmd):
        self._command_queue.put(cmd)

    def abort(self):
        # Method for use by main thread to signal an abort
        self._command_queue.put("abort")
        self._want_abort = True


class TaskManager(object):
    @classmethod
    def stop_all(cls):
        main_thread = threading.currentThread()
        for thread in threading.enumerate():
            if thread == main_thread:
                continue
            log.debug("attempting to reap %s" % thread)
            if thread.is_alive():
                thread.abort()
            thread.join()


class TestStatusThread(PygletTask):
    def task_setup(self, *args, **kwargs):
        self._count = 0
        
    def task(self):
        while True:
            time.sleep(0.2)
            log.debug("Thread awake!")
            self.notify("Number %d" % self._count)
            self._count += 1
            if self._count % 5 == 0:
                time.sleep(3)
            if self._want_abort or self._count > 100:
                return
