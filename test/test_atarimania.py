#!/usr/bin/env python
# -*- coding: utf-8 -*-

from dinoteeth_test import *

from dinoteeth.filescan import *
from dinoteeth.metadata import *

from dinoteeth.task import TaskManager
from dinoteeth.download import BackgroundHttpDownloader
from dinoteeth.games.atarimania import *

if __name__ == '__main__':
    import sys
    import logging
    
    logging.basicConfig(level=logging.DEBUG,
                        format='%(name)s: %(message)s',
                        )
    
    api = AtariMania_API()
        
    manager = TaskManager(None)
    downloader = BackgroundHttpDownloader()
    manager.start_dispatcher(downloader)
    
    tasks = set([Atari8BitSearch(api, "Jumpman"), Atari8BitSearch(api, "Bruce Lee")])
    for task in tasks:
        manager.add_task(task)
    
    while len(tasks):
        time.sleep(1)
        done = manager.get_finished()
        for task in done:
            print 'FINISHED:', str(task)
            tasks.remove(task)
    
    manager.shutdown()
