import os, logging

from thread import ThreadTaskManager, ProcessTaskManager

log = logging.getLogger("dinoteeth.updates")


class PosterLoadTask(object):
    def __init__(self, imdb_id, media_category, title):
        self.imdb_id = imdb_id
        self.media_category = media_category
        self.title = title
    
    def __str__(self):
        return "%s: imdb_id=%s" % (self.__class__.__name__, self.imdb_id)
        
    def __call__(self, posters=None, *args, **kwargs):
        posters.fetch_poster(self.imdb_id, self.media_category)
        return "Loaded artwork for %s" % self.title


class UpdateManager(object):
    poster_thread = None
    
    def __init__(self, window, event_name, db, mmdb, poster_fetcher):
        cls = self.__class__
        if cls.poster_thread is not None:
            raise RuntimeError("UpdateManager already initialized")
        cls.window = window
        cls.event_name = event_name
        cls.db = db
        cls.mmdb = mmdb
        cls.posters = poster_fetcher
        #cls.poster_thread = ThreadTaskManager(window, event_name, posters=cls.posters)
        cls.poster_thread = ProcessTaskManager(window, event_name, num_workers=1, posters=cls.posters)
    
    @classmethod
    def update_all_posters(cls):
#        cls.poster_thread.test()
        db = cls.db
        for i, title_key in enumerate(db.iter_title_keys()):
            if title_key not in db.title_key_to_imdb:
                continue
            imdb_id = db.title_key_to_imdb[title_key]
            if not cls.posters.has_poster(imdb_id):
                try:
                    media = cls.mmdb.get(imdb_id)
                    task = PosterLoadTask(imdb_id, media.media_category, media.title)
                    cls.poster_thread.add_task(task)
                except KeyError:
                    log.error("mmdb doesn't know about %s" % imdb_id)
