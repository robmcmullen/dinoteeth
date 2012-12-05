#!/usr/bin/env python
# -*- coding: utf-8 -*-

from dinoteeth_test import *

from dinoteeth.filescan import *
from dinoteeth.metadata import *

if __name__ == "__main__":
    import sys
    import dinoteeth.games
    import dinoteeth.home_theater
    from dinoteeth.utils import DBFacade
    from dinoteeth.database import HomeTheaterDatabase
    
#    import logging
#    logging.basicConfig(level=logging.DEBUG, format='%(name)s: %(message)s')
    
    zodb = DBFacade("Data.fs")
    db = HomeTheaterDatabase(zodb)
    
    for filename in sys.argv[1:]:
        db.add(filename)

    db.update_metadata()
    db.update_posters()
