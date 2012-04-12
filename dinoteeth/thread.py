import os, time, logging, threading, multiprocessing, Queue
import pyglet

log = logging.getLogger("dinoteeth.thread")
log.setLevel(logging.DEBUG)

class TestSleepTask(object):
    def __init__(self, num, sleep):
        self.num = num
        self.sleep = sleep
        
    def __call__(self, *args, **kwargs):
        log.debug("test task #%d starting!")
        time.sleep(self.sleep)
        return "test task #%d finished!" % self.num

class TaskManager(object):
    def add_task(self, task):
        print("Adding task %s" % str(task))
        self._tasks.put(task)
    
    def _notify(self, result):
        """Called from within the thread"""
        print "Got result: %s" % result
        pyglet.app.platform_event_loop.post_event(self._notify_window, self._notify_event, result)

    def abort(self):
        # Method for use by main thread to signal an abort
        self._want_abort = True
        self.add_task(None)
    
    def test(self, count=100, sleep=0.2):
        for i in range(count):
            t = sleep
            if i % 5 == 0:
                t = sleep * 5
            self.add_task(TestSleepTask(i, t))

    @classmethod
    def stop_all(cls):
        main_thread = threading.currentThread()
        for thread in threading.enumerate():
            if thread == main_thread:
                continue
            if not hasattr(thread, "abort"):
                # Not one of our managed threads
                continue
            log.debug("attempting to reap %s" % thread)
            if thread.is_alive():
                thread.abort()
            thread.join()


class ThreadTaskManager(threading.Thread, TaskManager):
    def __init__(self, notify_window, notify_event, *args, **kwargs):
        threading.Thread.__init__(self)
        self._notify_window = notify_window
        self._notify_event = notify_event
        self.args = args
        self.kwargs = kwargs
        self._want_abort = False
        self._tasks = Queue.Queue()
        self.setDaemon(True)
        self.start()
    
    def run(self):
        print("starting thread...")
        while True:
            print("waiting for tasks...")
            task = self._tasks.get(True) # blocking
            if task is None or self._want_abort:
                break
            result = task(*self.args, **self.kwargs)
            self._notify(result)
            if self._want_abort:
                break


class Worker(multiprocessing.Process):
    def __init__(self, task_queue, result_queue, *args, **kwargs):
        multiprocessing.Process.__init__(self)
        self._tasks = task_queue
        self._results = result_queue
        self.args = args
        self.kwargs = kwargs
        self.start()

    def run(self):
        while True:
            task = self._tasks.get() # block to wait for new task
            if task is None:
                # "poison pill" means shutdown this worker
                print("%s: finished" % self.name)
                self._results.put(WorkerFinished())
                break
            print("%s: running task %s" % (self.name, task))
            result = task(*self.args, **self.kwargs)
            print("%s: completed task %s with result %s" % (self.name, task, result))
            self._results.put(result)
        return

class WorkerFinished(object):
    pass

class ProcessTaskManager(threading.Thread, TaskManager):
    def __init__(self, notify_window, notify_event, num_workers=0, *args, **kwargs):
        threading.Thread.__init__(self)
        self._notify_window = notify_window
        self._notify_event = notify_event
        self.args = args
        self.kwargs = kwargs
        self._want_abort = False
        self._tasks = multiprocessing.Queue()
        self._results = multiprocessing.Queue()
        if num_workers < 1:
            try:
                num_workers = multiprocessing.cpu_count()
            except:
                num_workers = 1
        self._num_workers = num_workers
        self._workers = [Worker(self._tasks, self._results, *args, **kwargs) for i in range(num_workers)]
        self.setDaemon(True)
        self.start()
    
    def run(self):
        print("starting multiprocess manager thread...")
        while True:
            try:
                print("waiting for results...")
                result = self._results.get(True, 1.0) # blocking
                if type(result) is WorkerFinished:
                    self._num_workers -= 1
                else:
                    self._notify(result)
                if self._num_workers == 0:
                    return
            except Queue.Empty:
                pass

    def abort(self):
        # Method for use by main thread to signal an abort
        self._want_abort = True
        for i in range(self._num_workers):
            print "Sending poison pill"
            self.add_task(None)
