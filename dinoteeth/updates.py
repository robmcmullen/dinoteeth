import os, collections, logging

from thread import PygletCommandQueue

log = logging.getLogger("dinoteeth.updates")


class DatabaseTask(PygletCommandQueue):
    log = logging.getLogger("dinoteeth.database_task")
    
    def __init__(self, window, event_name, db, mmdb, poster_fetcher):
        PygletCommandQueue.__init__(self, window, event_name, db, mmdb, poster_fetcher)
        
    def task_setup(self, db, mmdb, poster_fetcher):
        self.db = db
        self.mmdb = mmdb
        self.posters = poster_fetcher
        self.log.debug("Database thread started")
        
    def task(self):
        while True:
            self.log.debug("Database thread waiting for command...")
            next = self._next_command()
            if next == "abort":
                return
            self.log.debug("Database thread found command: %s" % next)
            if next == "update_all_posters":
                self._update_all_posters()
            else:
                self.log.debug("Unknown database thread command: %s" % next)
    
    def _update_all_posters(self):
        db = self.db
        for i, title_key in enumerate(db.iter_title_keys()):
            if title_key not in db.title_key_to_imdb:
                continue
            imdb_id = db.title_key_to_imdb[title_key]
            if self.posters.has_poster(imdb_id):
                self.notify("Already loaded posters for imdb_id %s" % imdb_id)
            else:
                self.notify("Loading posters for imdb_id %s" % imdb_id)
                try:
                    media = self.mmdb.get(imdb_id)
                    self.posters.fetch_poster(imdb_id, media.media_category)
                except KeyError:
                    print "mmdb doesn't know about %s" % imdb_id
                    raise
            if self._want_abort:
                return
        self.notify("Finished loading posters")


class UpdateManager(object):
    db_thread = None
    
    def __init__(self, window, event_name, db, mmdb, poster_fetcher):
        if self.__class__.db_thread is None:
            self.__class__.db_thread = DatabaseTask(window, event_name, db, mmdb, poster_fetcher)
        else:
            raise RuntimeError("UpdateManager already initialized")
    
    @classmethod
    def update_all_posters(cls):
        cls.db_thread.put_command("update_all_posters")

