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
        
    def _start(self, processor):
        raise RuntimeError("Abstract method")
    
    def post_process(self):
        return []

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
        
    def _start(self, processor):
        log.debug("%s starting!" % self.get_name())
        time.sleep(self.sleep)

class TestProcessSleepTask(ProcessTask):
    def __init__(self, num, sleep):
        Task.__init__(self)
        self.num = num
        self.sleep = sleep
    
    def get_name(self):
        return "process sleep task #%d, delay=%ss" % (self.num, self.sleep)
        
    def _start(self, processor):
        log.debug("%s starting!" % self.get_name())
        time.sleep(self.sleep)


class TaskDispatcher(object):
    def __init__(self, share_input_queue_with=None):
        self._want_abort = False
        if share_input_queue_with is not None:
            self._queue = share_input_queue_with._queue
        else:
            self._queue = Queue.Queue()
    
    def set_finish_queue(self, finish_queue):
        self._finished = finish_queue
    
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
            self._finished.put(task)

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
            self._finished.put(task)
            
            if task is None:
                log.debug("%s: Stopping process %s" % (self.name, self._worker))
                self._worker.join()
                log.debug("%s: Exiting dispatcher %s" % (self.name, self.name))
                break


class TaskManager(object):
    def __init__(self):
        log = logging.getLogger(self.__class__.__name__)
        self._finished = Queue.Queue()
        self.processors = []
    
    def find_processor(self, task):
        for processor in self.processors:
            if processor.can_handle(task):
                return processor
        return None
            
    def start_processor(self, processor):
        log.debug("Adding processor %s" % str(processor))
        processor.set_finish_queue(self._finished)
        processor.start_processing()
        self.processors.append(processor)
            
    def add_task(self, task):
        processor = self.find_processor(task)
        if processor is not None:
            log.debug("Adding task %s to %s" % (str(task), str(processor)))
            processor.add_task(task)
        else:
            log.debug("No processor for task %s" % str(task))
    
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
            if task.parent is not None:
                log.debug("  subtask of %s" % str(task.parent))
            sub_tasks = task.post_process()
            if sub_tasks:
                for sub_task in sub_tasks:
                    sub_task.parent = task
                    task.children_running += 1
                    self.add_task(sub_task)
            else:
                t = task
                while t.parent is not None:
                    t.parent.children_running -= 1
                    if t.parent.children_running == 0:
                        t = t.parent
                    else:
                        break
                if t.parent is None and t.children_running == 0:
                    log.debug("marking root task %s completed" % str(t))
                    root_tasks_done.add(t)
        return root_tasks_done
    
    def shutdown(self):
        for processor in self.processors:
            processor.abort()
        for processor in self.processors:
            processor.join()


if __name__ == '__main__':
    manager = TaskManager()
    processor1 = ThreadTaskDispatcher()
    manager.start_processor(processor1)
    processor2 = ThreadTaskDispatcher(processor1)
    manager.start_processor(processor2)
    processor3 = ProcessTaskDispatcher()
    manager.start_processor(processor3)
    for i in range(3):
        processor_i = ProcessTaskDispatcher(processor3)
        manager.start_processor(processor_i)
    
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
