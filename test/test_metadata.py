#!/usr/bin/env python
# -*- coding: utf-8 -*-

from dinoteeth_test import *

from dinoteeth.filescan import *
from dinoteeth.metadata import *

if __name__ == "__main__":
    import sys
    import dinoteeth.games
    import dinoteeth.games.atarimania
    import dinoteeth.home_theater
    
#    import logging
#    logging.basicConfig(level=logging.DEBUG, format='%(name)s: %(message)s')
    
    for filename in sys.argv[1:]:
        file = MediaFile(filename)
        print file
        print file.scan.title_key

        loader = MetadataLoader.get_loader(file)
        guesses = loader.search(file.scan.title_key)
        print guesses
        
        if len(guesses) > 0:
            metadata = loader.get_metadata(guesses[0])
            print unicode(metadata).encode("utf-8")
            
            loader.fetch_posters(metadata)
        else:
            print "No search results for %s" % str(file.scan.title_key)
