Prerequisites
=============

requests
imdbpy
zodb
pyinotify


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
