Prerequisites
=============

Native libraries
----------------

SDL
SDL_gfx
SDL_image
SDL_Pango

Python libraries
----------------

PIL
requests
beautifulsoup4
imdbpy
guessit
zodb3
pyinotify
kaa-base
kaa.metadata (from https://github.com/robmcmullen/kaa-metadata for Atari support)

Note: PyGame or other SDL bindings are not required because direct ctypes
bindings are included


Testing
=======

Start ZEO with a test database and port::

    runzeo -a 3444 -f /tmp/test.fs

Create a test config file, containing at least::

    [defaults]
    metadata_root = tmp-multi
    poster_width = 342
    db_host = localhost:3444

    [media_paths]
    /path/to/media/directory = autodetect, basename

Start the monitor process in another terminal with::

    python monitor.py -c [path to config file]

And, in yet another terminal, start the program with::

    python run.py -w -c [path to config file]
