import os, time, logging, threading, Queue
import asyncore, socket, urlparse
from cStringIO import StringIO

from task import Task, ThreadTaskDispatcher, TaskManager

class HttpClient(asyncore.dispatcher):
    # Based on an example in Doug Hellmann's PyMOTW:
    # http://www.doughellmann.com/PyMOTW/asyncore/
    def __init__(self, url, consumer, finished_callback=None, finished_data=None):
        self.url = url
        self.consumer = consumer
        self.finished_callback = finished_callback
        self.finished_data = finished_data
        self.log = logging.getLogger(self.url)
        self.parsed_url = urlparse.urlparse(url)
        asyncore.dispatcher.__init__(self)
        self.write_buffer = 'GET %s HTTP/1.0\r\nHost: %s\r\nAccept:*/*;q=0.8\r\n\r\n' % (self.parsed_url.path, self.parsed_url.netloc)
        self.create_socket(socket.AF_INET, socket.SOCK_STREAM)
        address = (self.parsed_url.netloc, 80)
        self.log.debug('connecting to %s', address)
        self.connect(address)

    def handle_connect(self):
        self.log.debug('handle_connect()')

    def handle_close(self):
        self.log.debug('handle_close()')
        self.consumer.close()
        self.close()
        if self.finished_callback:
            self.finished_callback(self, self.finished_data)

    def writable(self):
        is_writable = (len(self.write_buffer) > 0)
        if is_writable:
            self.log.debug('writable() -> %s', is_writable)
        return is_writable
    
    def readable(self):
        self.log.debug('readable() -> True')
        return True

    def handle_write(self):
        sent = self.send(self.write_buffer)
        self.log.debug('handle_write() -> "%s"', self.write_buffer[:sent])
        self.write_buffer = self.write_buffer[sent:]

    def handle_read(self):
        data = self.recv(8192)
        self.log.debug('handle_read() -> %d bytes', len(data))
        if len(data) > 0:
            self.consumer.write(data)

class Consumer(object):
    def __init__(self):
        self.log = logging.getLogger(self.__class__.__name__)
        self.size = 0
    
    def write(self, data):
        pass
    
    def close(self):
        pass

class PrintConsumer(Consumer):
    def write(self, data):
        self.log.debug('absorbing %d bytes', len(data))
        self.size += len(data)

class FileConsumer(Consumer):
    def __init__(self, *args, **kwargs):
        Consumer.__init__(self)
        self.get_file(*args)
        self.include_header = kwargs.get('include_header', False)
        self.header = ""
        self.header_complete = False
    
    def get_file(self, *args):
        self.path = args[0]
        self.temp_path = self.path + ".part"
        self.fh = open(self.temp_path, "wb")
        
    def write(self, data):
        self.log.debug('saving %d bytes', len(data))
        if not self.header_complete:
            self.header += data
            i = self.header.find("\r\n\r\n")
            if i < 0:
                return
            data = self.header[i+4:]
            self.header = self.header[:i+4]
            self.header_complete = True
            if self.include_header:
                self.fh.write(self.header)
        self.log.debug('header: %s' % str(self.header))
        self.fh.write(data)
        self.size += len(data)
    
    def close(self):
        self.log.debug('saved %d bytes to %s', self.size, self.temp_path)
        self.fh.close()
        if os.path.exists(self.path):
            os.remove(self.path)
        os.rename(self.temp_path, self.path)

class MemoryConsumer(FileConsumer):
    def get_file(self, *args):
        self.fh = StringIO()
    
    def close(self):
        self.log.debug('saved %d bytes to StringIO object', self.size)
        self.data = self.fh.getvalue()
        self.fh.close()


class DownloadTask(Task):
    def __init__(self, url, path=None, overwrite=False, **kwargs):
        Task.__init__(self)
        self.url = url
        self.path = path
        self.overwrite = overwrite
        self.kwargs = kwargs
        self.size = 0
    
    def _get_consumer(self):
        if self.path is None:
            return MemoryConsumer(**self.kwargs)
        return FileConsumer(self.path, **self.kwargs)
    
    def _is_cached(self):
        if self.path is not None and os.path.exists(self.path) and not self.overwrite:
            self.size = os.path.getsize(self.path)
            return True
        return False
    
    def _start(self, dispatcher):
        found = self._is_cached()
        if found:
            dispatcher._manager._task_done(self)
        else:
            consumer = self._get_consumer()
            client = HttpClient(self.url, consumer, self._finished_callback, dispatcher)
    
    def _finished_callback(self, client, dispatcher):
        self.size = client.consumer.size
        if self.path is None:
            self.data = client.consumer.data
        dispatcher._manager._task_done(self)

class BackgroundHttpDownloader(ThreadTaskDispatcher):
    def __init__(self):
        ThreadTaskDispatcher.__init__(self)
        self._counter = 0
        self._timeout = 1
        self._max_simultaneous = 5
    
    def can_handle(self, task):
        return isinstance(task, DownloadTask)
    
    def run(self):
        self.log.debug("starting thread...")
        while True:
            if self._want_abort:
                break

            if asyncore.socket_map:
                self._counter += 1
                self.log.debug('counter=%s, # sockets = %d', self._counter, len(asyncore.socket_map))
                asyncore.loop(timeout=self._timeout, count=1)
            else:
                self.log.debug("No current downloads; blocking for a client...")
                delay = time.time()
                task = self._queue.get(True)
                if task is None:
                    return
                task._start(self)
                delay = time.time() - delay
                self.log.debug("blocked %ss; found client %s", delay, task.url)
            
            # attempt to start as many downloads as we can
            while len(asyncore.socket_map) < self._max_simultaneous:
                try:
                    task = self._queue.get(False)
                    if task is None:
                        return
                    task._start(self)
                    self.log.debug("found client %s", task.url)
                except Queue.Empty:
                    break


if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG,
                        format='%(name)s: %(message)s',
                        )

    manager = TaskManager(lambda s: None)
    downloader = BackgroundHttpDownloader()
    manager.start_dispatcher(downloader)
    manager.add_task(DownloadTask('http://www.python.org/', "python.html", overwrite=True))
    manager.add_task(DownloadTask('http://www.doughellmann.com/PyMOTW/contents.html',"pymotw.html"))
    manager.add_task(DownloadTask('http://docs.python.org/release/2.6.8/_static/py.png', "py.png"))
    manager.add_task(DownloadTask('http://docs.python.org/release/2.6.8/_static/py.png', "py2.png"))
    manager.add_task(DownloadTask('http://docs.python.org/release/2.6.8/_static/py.png', "py3.png"))
    manager.add_task(DownloadTask('http://image.tmdb.org/t/p/w342/vpk4hLyiuI2SqCss0T3jeoYcL8E.jpg', "test.jpg"))
    for i in range(10):
        time.sleep(1)
        tasks = manager.get_finished()
        for task in tasks:
            print 'FINISHED:', task.size, 'bytes for', task.path, 'from', task.url
        if i == 5:
            manager.add_task(DownloadTask('http://www.python.org/images/python-logo.gif', "bigpy.gif"))
            
    manager.shutdown()
