#!/usr/bin/env python
# -*- coding: utf-8 -*-

from dinoteeth_test import *

from dinoteeth.filescan import *
from dinoteeth.metadata import *

if __name__ == "__main__":
    import sys
    import dinoteeth.filescan.home_theater
    import dinoteeth.filescan.games
    import dinoteeth.metadata.home_theater
    
    proxies = Proxies(
        imdb_cache_dir="imdb_cache",
        tmdb_cache_dir="tmdb_cache",
        tvdb_cache_dir="tvdb_cache",
        language="English")

    for filename in sys.argv[1:]:
        file = MediaFile(filename)
        print file
        print file.scan.title_key

        loader = get_loader(file, proxies)
        guesses = loader.search(file.scan.title_key)
        print guesses
        