#!/usr/bin/env python
# -*- coding: utf-8 -*-

from dinoteeth_test import *

from dinoteeth.filescan import *
from dinoteeth.metadata import *

from dinoteeth.task import TaskManager
from dinoteeth.download import BackgroundHttpDownloader
from dinoteeth.home_theater.proxies import *

if __name__ == '__main__':
    import sys
    import logging
    
    logging.basicConfig(level=logging.DEBUG,
                        format='%(name)s: %(message)s',
                        )
    
    api = IMDbProxy("/tmp")
        
    tasks = [IMDbSearchTask(api, "The Man Who Never Was"), IMDbMovieDetailTask(api, "tt0049471")]
#    for task in tasks:
#        if task._is_cached():
#            task.success_callback()
#            sys.exit()
    
    manager = TaskManager(None)
    downloader = BackgroundHttpDownloader()
    manager.start_dispatcher(downloader)
    
    for task in tasks:
        manager.add_task(task)

    while len(tasks):
        time.sleep(1)
        done = manager.get_finished()
        for task in done:
            print 'FINISHED:', str(task)
            tasks.remove(task)
    
    manager.shutdown()
