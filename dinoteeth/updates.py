import os, time, logging

from thread import ThreadTaskManager, ProcessTaskManager, TestSleepTask

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

class ThumbnailLoadTask(object):
    def __init__(self, imgpath):
        self.imgpath = imgpath
    
    def __str__(self):
        return "%s: thumbnail=%s" % (self.__class__.__name__, self.imgpath)
    
    def __call__(self, thumbnails=None, *args, **kwargs):
        try:
            thumbnails.get_thumbnail_file(self.imgpath, True)
            return "Created thumbnail image for %s" % os.path.basename(self.imgpath)
        except:
            return "Failed creating thumbnail image for %s" % os.path.basename(self.imgpath)

class TimerTask(object):
    def __init__(self, delay, expire_time, repeat=True):
        self.delay = delay
        self.expire_time = expire_time
        self.repeat = repeat
    
    def __call__(self, *args, **kwargs):
        time.sleep(self.delay)
        if time.time() >= self.expire_time:
            self.repeat = False


class UpdateManager(object):
    poster_thread = None
    
    def __init__(self, window, event_name, db, mmdb, poster_fetcher, thumbnail_loader):
        cls = self.__class__
        if cls.poster_thread is not None:
            raise RuntimeError("UpdateManager already initialized")
        cls.window = window
        cls.event_name = event_name
        cls.db = db
        cls.mmdb = mmdb
        cls.posters = poster_fetcher
        cls.thumbnails = thumbnail_loader
        cls.poster_thread = ProcessTaskManager(window, event_name, num_workers=1, posters=cls.posters, thumbnails=cls.thumbnails)
        cls.timer_thread = ThreadTaskManager(window, 'on_timer')
    
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
    
    @classmethod
    def create_thumbnail(cls, imgpath):
        task = ThumbnailLoadTask(imgpath)
        cls.poster_thread.add_task(task)
    
    @classmethod
    def test(cls, num=4, delay=.5):
        for i in range(num):
            task = TestSleepTask(i + 1, delay)
            cls.poster_thread.add_task(task)
    
    @classmethod
    def start_ticks(cls, delay, expire_time):
        task = TimerTask(delay, expire_time)
        cls.timer_thread.add_task(task)
    
    @classmethod
    def stop_ticks(cls):
        task = TimerTask(0, 0, repeat=False)
        cls.timer_thread.add_task(task)
    
    @classmethod
    def stop_all(cls):
        ProcessTaskManager.stop_all()
