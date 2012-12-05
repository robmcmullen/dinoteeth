#!/usr/bin/env python2.6

# Media update monitor for dinoteeth

from dinoteeth.main import run_monitor

if __name__ == "__main__":
    import sys
    
    for arg in sys.argv:
        if arg == "-d" or arg == "--debug":
            import logging
            logging.basicConfig(level=logging.DEBUG, format='%(name)s: %(message)s')

    run_monitor()
