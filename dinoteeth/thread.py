import os, time, logging, Queue
from threading import Thread
import pyglet

log = logging.getLogger("dinoteeth.thread")


class PygletTask(Thread):
    def __init__(self, notify_window, notify_event, *args, **kwargs):
        Thread.__init__(self)
        self._notify_window = notify_window
        self._notify_event = notify_event
        self.init_hook()
        self.task_setup(*args, **kwargs)
        TaskManager.new_task(self)
        self.start()
    
    def init_hook(self):
        self._want_abort = False

    def run(self):
        self.task()
        TaskManager.completed_task(self)
    
    def notify(self, *args, **kwargs):
        """Called from within the thread"""
        pyglet.app.platform_event_loop.post_event(self._notify_window, self._notify_event, *args, **kwargs)

    def abort(self):
        # Method for use by main thread to signal an abort
        self._want_abort = True

class PygletCommandQueue(PygletTask):
    def init_hook(self):
        PygletTask.init_hook(self)
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
    all_tasks = set()
    completed_tasks = Queue.Queue()
    
    @classmethod
    def housekeeping(cls):
        try:
            task = cls.completed_tasks.get(False)
            if task.is_alive():
                # Shouldn't happen
                task.abort()
                task.join()
            cls.all_tasks.discard(task)
            log.debug("reaped task %s" % task)
        except:
            log.debug("no tasks to reap")
    
    @classmethod
    def new_task(cls, task):
        cls.housekeeping()
        cls.all_tasks.add(task)
    
    @classmethod
    def completed_task(cls, task):
        """Called from a thread"""
        cls.completed_tasks.put(task)
    
    @classmethod
    def stop_all(cls):
        cls.housekeeping()
        while True:
            try:
                task = cls.all_tasks.pop()
            except KeyError:
                break
            log.debug("attempting to reap %s" % task)
            if task.is_alive():
                task.abort()
            task.join()


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
