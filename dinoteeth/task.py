import os, time, logging, threading, multiprocessing, Queue

# Utilities for thread and process based tasks



# Don't use the logger module in anything using multiprocessing! It can cause
# deadlocks.  I.e. don't use this:
#### log = logging.getLogger("dinoteeth.task")

log = multiprocessing.log_to_stderr()
#log.setLevel(logging.INFO)



class Task(object):
    def __init__(self):
        self.parent = None
        self.children_running = 0
        self.children_scheduled = []
        self.error = None
        self.exception = None
    
    def __str__(self):
        status = self.get_name()
        if not self.success():
            if self.error is not None:
                status += " Failed: %s" % self.error
            else:
                status += " Exception: %s" % self.exception
        return status
    
    def success(self):
        return self.error is None and self.exception is None
    
    def get_name(self):
        return self.__class__.__name__
        
    def _start(self, dispatcher):
        raise RuntimeError("Abstract method")
    
    def _success_message(self):
        return None
    
    def _failed_message(self):
        return None

    def _get_status_message(self):
        if self.success():
            return self._success_message()
        else:
            return self._failed_message()
    
    def success_callback(self):
        """Called in main thread if task completes successfully.
        
        This method's primary use is to start any subtasks that depend on this
        task.  Note that since it occurs in the main thread, GUI methods may
        be safely called.
        
        The task is not returned by TaskManager.get_finished until all subtasks
        are complete.
        
        @returns: list of sub-tasks to process
        """
        return []
    
    def failure_callback(self):
        """Called in main thread if task fails during the thread processing.
        
        This method's primary use is to start any subtasks that might work
        around the error encountered during this task.  Note that since it
        occurs in the main thread, GUI methods may be safely called.
        
        The task is not returned by TaskManager.get_finished until all subtasks
        are complete.
        
        @returns: list of sub-tasks to process
        """
        return []
    
    def subtasks_complete_callback(self):
        """Called in main thread when all subtasks have completed.
        
        Since it occurs in the main thread, GUI methods may be safely called.
        
        This method is called when all subtasks have been completed,
        successfully or not.  It is called iff some subtasks were
        created in either success_callback or failure_callback.
        """
        pass
    
    def root_task_complete_callback(self):
        """Called in main thread when a directly-added task completes.
        
        Since it occurs in the main thread, GUI methods may be safely called.
        
        This method is called when a root task is marked as completed by
        TaskManager.get_finished.  This method will not be called on subtasks
        added by success_callback or failure_callback.
        """
        pass

class ThreadTask(Task):
    pass

class ProcessTask(Task):
    def _start(self, results):
        raise RuntimeError("Abstract method")

class TestSleepTask(ThreadTask):
    def __init__(self, num, sleep):
        Task.__init__(self)
        self.num = num
        self.sleep = sleep
    
    def get_name(self):
        return "thread sleep task #%d, delay=%ss" % (self.num, self.sleep)
        
    def _start(self, dispatcher):
        log.debug("%s starting!" % self.get_name())
        time.sleep(self.sleep)

class TestProcessSleepTask(ProcessTask):
    def __init__(self, num, sleep):
        Task.__init__(self)
        self.num = num
        self.sleep = sleep
    
    def get_name(self):
        return "process sleep task #%d, delay=%ss" % (self.num, self.sleep)
        
    def _start(self, dispatcher):
        log.debug("%s starting!" % self.get_name())
        time.sleep(self.sleep)


class TaskDispatcher(object):
    def __init__(self, share_input_queue_with=None):
        self._want_abort = False
        if share_input_queue_with is not None:
            self._queue = share_input_queue_with._queue
        else:
            self._queue = Queue.Queue()
    
    def set_manager(self, manager):
        self._manager = manager
    
    def start_processing(self):
        raise RuntimeError("Abstract method")
    
    def can_handle(self, task):
        return False
    
    def add_task(self, task):
        self._queue.put(task)

    def abort(self):
        # Method for use by main thread to signal an abort
        self._want_abort = True
        self._queue.put(None)

class ThreadTaskDispatcher(threading.Thread, TaskDispatcher):
    def __init__(self, share_input_queue_with=None):
        threading.Thread.__init__(self)
        TaskDispatcher.__init__(self, share_input_queue_with)
        self.log = log
    
    def start_processing(self):
#        self.setDaemon(True)
        self.start()
        
    def can_handle(self, task):
        return isinstance(task, ThreadTask)
    
    def run(self):
        log.debug("starting thread...")
        while True:
            log.debug("%s waiting for tasks..." % self.name)
            task = self._queue.get(True) # blocking
            if task is None or self._want_abort:
                break
            try:
                task._start(self)
            except Exception, e:
                import traceback
                task.exception = traceback.format_exc()
            self._manager._task_done(task)

def testsleep(dum):
    print "Starting ..."
    time.sleep(1)
    print "Done..."


class Worker(multiprocessing.Process):
    def __init__(self, task_queue, finished_queue):
        multiprocessing.Process.__init__(self)
        self._tasks = task_queue
        self._finished = finished_queue
        self.start()

    def run(self):
        while True:
            log.debug("%s: worker waiting for task" % self.name)
            task = self._tasks.get() # block to wait for new task
            log.debug("%s: worker found task %s" % (self.name, str(task)))
            if task is None:
                # "poison pill" means shutdown this worker
                log.debug("%s: poison pill received. Stopping" % self.name)
                self._finished.put(None)
                break
            try:
                task._start(self)
            except Exception, e:
                import traceback
                task.exception = traceback.format_exc()
            self._finished.put(task)

class ProcessTaskDispatcher(ThreadTaskDispatcher):
    def __init__(self, *args, **kwargs):
        ThreadTaskDispatcher.__init__(self, *args, **kwargs)
        self._multiprocessing_tasks = multiprocessing.Queue()
        self._multiprocessing_finished = multiprocessing.Queue()
        self._worker = Worker(self._multiprocessing_tasks, self._multiprocessing_finished)
        log.debug("worker %s: status = %s" % (self._worker, self._worker.exitcode))
        
    def can_handle(self, task):
        return isinstance(task, ProcessTask)
    
    def run(self):
        log.debug("%s: starting process task dispatcher thread..." % self.name)
        while True:
            log.debug("%s: waiting for tasks..." % self.name)
            task = self._queue.get(True) # blocking
            
            # Send task to worker and wait for it to finish
            log.debug("%s: sending task '%s' to process %s" % (self.name, task, self._worker))
            self._multiprocessing_tasks.put(task)
            task = self._multiprocessing_finished.get(True)
            
            # Send results back to main thread
            self._manager._task_done(task)
            
            if task is None:
                log.debug("%s: Stopping process %s" % (self.name, self._worker))
                self._worker.join()
                log.debug("%s: Exiting dispatcher %s" % (self.name, self.name))
                break


class Timer(threading.Thread):
    def __init__(self, event_callback, resolution=.2):
        threading.Thread.__init__(self)
        self._event_callback = event_callback
        self._event = threading.Event()
        self._resolution = resolution
        self._expire_time = time.time()
        self._want_abort = False
        self.start()

    def run(self):
        while self._event.wait():
            while self._event.is_set():
                if self._want_abort:
                    return
                time.sleep(self._resolution)
                print "timer!!!!"
                self._event_callback()
                if time.time() > self._expire_time:
                    self.stop_ticks()
            if self._want_abort:
                return
            self._event_callback()

    def start_ticks(self, resolution, expire_time):
        self._resolution = resolution
        self._expire_time = expire_time
        self._event.set()

    def stop_ticks(self):
        if not self._want_abort:
            self._event.clear()

    def abort(self):
        print "stopping timer"
        self._want_abort = True
        self._event.set()

class TaskManager(object):
    def __init__(self, event_callback):
        log = logging.getLogger(self.__class__.__name__)
        self.event_callback = event_callback
        self._finished = Queue.Queue()
        self.dispatchers = []
        self.timer = Timer(event_callback)
    
    def start_ticks(self, resolution, expire_time):
        self.timer.start_ticks(resolution, expire_time)
    
    def stop_ticks(self):
        self.timer.stop_ticks()

    def find_dispatcher(self, task):
        for dispatcher in self.dispatchers:
            if dispatcher.can_handle(task):
                return dispatcher
        return None
            
    def start_dispatcher(self, dispatcher):
        log.debug("Adding dispatcher %s" % str(dispatcher))
        dispatcher.set_manager(self)
        dispatcher.start_processing()
        self.dispatchers.append(dispatcher)
            
    def add_task(self, task):
        dispatcher = self.find_dispatcher(task)
        if dispatcher is not None:
            log.debug("Adding task %s to %s" % (str(task), str(dispatcher)))
            dispatcher.add_task(task)
        else:
            log.debug("No dispatcher for task %s" % str(task))
        return dispatcher is not None
    
    def _task_done(self, task):
        """Called from threads to report completed tasks
        
        If event handler is defined, also calls that function to report to the
        UI that a task is available.
        """
        self._finished.put(task)
        if self.event_callback is not None:
            if task is not None:
                message = task._get_status_message()
            else:
                message = None
            self.event_callback(message)
    
    def get_finished(self):
        done = set()
        try:
            while True:
                task = self._finished.get(False)
                done.add(task)
        except Queue.Empty:
            pass
        root_tasks_done = set()
        for task in done:
            log.debug("task %s completed" % str(task))
            if task is None:
                # Skip any poison pill tasks
                continue
            if task.parent is not None:
                log.debug("  subtask of %s" % str(task.parent))
            if task.success():
                sub_tasks = task.success_callback()
            else:
                sub_tasks = task.failure_callback()
            if sub_tasks:
                for sub_task in sub_tasks:
                    sub_task.parent = task
                    scheduled = self.add_task(sub_task)
                    if scheduled:
                        task.children_running += 1
                        task.children_scheduled.append(task)
                    else:
                        # remove parent if task wasn't scheduled.  Can't simply
                        # add parent after add_task because the task may have
                        # already been started by the thread
                        sub_task.parent = None
            else:
                t = task
                while t.parent is not None:
                    t.parent.children_running -= 1
                    if t.parent.children_running == 0:
                        t.parent.subtasks_complete_callback()
                        t = t.parent
                    else:
                        break
                if t.parent is None and t.children_running == 0:
                    log.debug("marking root task %s completed" % str(t))
                    t.root_task_complete_callback()
                    root_tasks_done.add(t)
        return root_tasks_done
    
    def shutdown(self):
        for dispatcher in self.dispatchers:
            dispatcher.abort()
        self.timer.abort()
        for dispatcher in self.dispatchers:
            dispatcher.join()
        self.timer.join()


if __name__ == '__main__':
    import functools
    
    def post_event(event_name, *args):
        print "event: %s.  args=%s" % (event_name, str(args))
        
    def get_event_callback(event):
        callback = functools.partial(post_event, event)
        return callback
    
    callback = get_event_callback("on_status_change")
    manager = TaskManager(callback)
    dispatcher1 = ThreadTaskDispatcher()
    manager.start_dispatcher(dispatcher1)
    dispatcher2 = ThreadTaskDispatcher(dispatcher1)
    manager.start_dispatcher(dispatcher2)
    dispatcher3 = ProcessTaskDispatcher()
    manager.start_dispatcher(dispatcher3)
    for i in range(3):
        dispatcher_i = ProcessTaskDispatcher(dispatcher3)
        manager.start_dispatcher(dispatcher_i)
    
    manager.add_task(TestSleepTask(1, 1))
    manager.add_task(TestSleepTask(2, 1))
    manager.add_task(TestSleepTask(3, 3))
    manager.add_task(TestSleepTask(4, 1))
    manager.add_task(TestSleepTask(5, 1))
    manager.add_task(TestProcessSleepTask(10, .1))
    manager.add_task(TestProcessSleepTask(11, .1))
    manager.add_task(TestProcessSleepTask(12, .3))
    manager.add_task(TestProcessSleepTask(13, .1))
    manager.add_task(TestProcessSleepTask(14, .1))
    for i in range(5):
        time.sleep(1)
        tasks = manager.get_finished()
        for task in tasks:
            print 'FINISHED:', str(task)

#    manager.add_task(TestProcessSleepTask(6, 1))
    manager.shutdown()
    tasks = manager.get_finished()
    for task in tasks:
        print 'FINISHED:', str(task)
    for i in range(5):
        time.sleep(1)
        tasks = manager.get_finished()
        for task in tasks:
            print 'FINISHED:', str(task)
