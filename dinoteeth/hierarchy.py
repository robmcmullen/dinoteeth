import os, sys, glob, re, logging, time

from model import MenuItem, MenuPopulator
from metadata import MovieMetadata, SeriesMetadata

logging.basicConfig(level=logging.WARNING)

log = logging.getLogger("dinoteeth.hierarchy")


class MMDBPopulator(MenuPopulator):
    def iter_image_path(self, artwork_loader):
        for media in self.media:
            imgpath = artwork_loader.get_poster_filename(media.id)
            if imgpath is not None:
                yield imgpath

class TopLevelLookup(MMDBPopulator):
    def __init__(self, config, metadata_classes):
        MMDBPopulator.__init__(self, config)
        self.metadata_classes = metadata_classes
        self.media_categories = [m.media_category for m in metadata_classes]
    
    def get_media(self):
        media = self.config.mmdb.get_media_by(self.media_categories, None, "")
        return media
    
    media = property(get_media)
        
    def iter_create(self):
        yield "All", MediaLookup(self.config, self.media_categories)
        yield "Recently Added", RecentLookup(self.config, self.media_categories)
        
        # Note that all credit maps are the same because it is defined as a
        # class attribute in the base class
        credit_map = self.metadata_classes[0].credit_map
        for title, credit, limit in credit_map:
            if limit is None or limit in self.media_categories:
                yield title, CreditLookup(self.config, self.media_categories, credit)

    def get_metadata(self):
        return {
            'imagegen': self.thumbnail_mosaic,
            }

class RecentLookup(MMDBPopulator):
    def __init__(self, config, media_categories=None):
        MMDBPopulator.__init__(self, config)
        self.media_categories = media_categories
    
    def get_media(self):
        media = self.config.mmdb.get_media_by(self.media_categories, "date_added", "")
        return media
    
    media = property(get_media)
        
    def iter_create(self):
        yield "Last Week", MediaLookup(self.config, self.media_categories, "date_added", value=lambda m: m >= time.time() - 7*24*3600)
        yield "Last Month", MediaLookup(self.config, self.media_categories, "date_added", value=lambda m: m >= time.time() - 31*24*3600)
        yield "Last 2 Months", MediaLookup(self.config, self.media_categories, "date_added", value=lambda m: m >= time.time() - 62*24*3600)
        yield "Last 3 Months", MediaLookup(self.config, self.media_categories, "date_added", value=lambda m: m >= time.time() - 93*24*3600)
        yield "Last 6 Months", MediaLookup(self.config, self.media_categories, "date_added", value=lambda m: m >= time.time() - 182*24*3600)
        yield "Last Year", MediaLookup(self.config, self.media_categories, "date_added", value=lambda m: m >= 365*24*3600)

    def get_metadata(self):
        return {
            'imagegen': self.thumbnail_mosaic,
            }

class CreditLookup(MMDBPopulator):
    def __init__(self, config, media_categories=None, credit=None):
        MMDBPopulator.__init__(self, config)
        self.media_categories = media_categories
        self.credit = credit
    
    def iter_create(self):
        items = self.config.mmdb.get_credit_entries(self.media_categories, self.credit)
        items.sort()
#        print "credit=%s, media_category=%s: %s" % (self.credit, self.media_categories, str(items))
        for item in items:
            if hasattr(item, 'imdb_prefix'):
                name = unicode(item)
            else:
                name = item
            name = unicode(item)
            yield name, MediaLookup(self.config, self.media_categories, self.credit, item)


class MediaLookup(MMDBPopulator):
    def __init__(self, config, media_categories=None, credit=None, value=""):
        MMDBPopulator.__init__(self, config)
        self.media_categories = media_categories
        self.credit = credit
        self.value = value
    
    def get_media(self):
        media = self.config.mmdb.get_media_by(self.media_categories, self.credit, self.value)
        return media
    
    media = property(get_media)
        
    def iter_create(self):
        for m in self.media:
            if not self.media_categories or (m.media_category in self.media_categories):
                if m.media_category == "series":
                    yield unicode(m.title), SeriesTopLevel(self.config, m.id)
                elif m.media_category == "movies":
                    yield unicode(m.title), MovieTopLevel(self.config, m.id)
    
    def get_metadata(self):
        return {
            'imagegen': self.thumbnail_mosaic,
            }


class PlayableEntries(MMDBPopulator):
    def __call__(self, parent):
        items = []
        for title, playable in self.iter_create():
            items.append((title, playable))
        if self.autosort:
            items.sort()
        for title, playable in items:
            item = MenuItem(title, action=playable.play, metadata=playable.get_metadata())
            yield item


class MovieTopLevel(PlayableEntries):
    def __init__(self, config, imdb_id):
        MMDBPopulator.__init__(self, config)
        self.imdb_id = imdb_id
        
    def iter_create(self):
        media_scans = self.config.db.get_all_with_imdb_id(self.imdb_id)
        media_scans.sort()
        for m in media_scans:
            yield unicode(m.display_title), MediaPlay(self.config, self.imdb_id, m)
            if m.is_paused():
                yield "  Resume", MediaPlay(self.config, self.imdb_id, m, resume=True)
                
    
    def get_metadata(self):
        return {
            'mmdb': self.config.mmdb.get(self.imdb_id),
            }


class SeriesTopLevel(MMDBPopulator):
    def __init__(self, config, imdb_id):
        MMDBPopulator.__init__(self, config)
        self.imdb_id = imdb_id
        
    def iter_create(self):
        media_scans = self.config.db.get_all_with_imdb_id(self.imdb_id)
        seasons = media_scans.get_seasons()
        for s in seasons:
            episodes = media_scans.get_episodes(s)
            yield u"Season %d" % s, SeriesEpisodes(self.config, self.imdb_id, s, episodes)
    
    def get_metadata(self):
        return {
            'mmdb': self.config.mmdb.get(self.imdb_id),
            }


class SeriesEpisodes(PlayableEntries):
    def __init__(self, config, imdb_id, season, episodes):
        PlayableEntries.__init__(self, config)
        self.imdb_id = imdb_id
        self.season = season
        self.episodes = episodes
        
    def iter_create(self):
        for m in self.episodes:
            yield unicode(m.display_title), MediaPlay(self.config, self.imdb_id, m, season=self.season)
            if m.is_paused():
                yield "  Resume (Paused at %s)" % m.paused_at_text(), MediaPlay(self.config, self.imdb_id, m, season=self.season, resume=True)

    def get_metadata(self):
        return {
            'mmdb': self.config.mmdb.get(self.imdb_id),
            'season': self.season,
            }


class MediaPlay(MMDBPopulator):
    def __init__(self, config, imdb_id, media_scan, season=None, resume=False):
        MMDBPopulator.__init__(self, config)
        self.imdb_id = imdb_id
        self.media_scan = media_scan
        self.season = season
        self.resume = resume
        
    def play(self, config=None):
        self.config.prepare_for_external_app()
        client = self.config.get_media_client()
        if self.resume:
            resume_at = self.media_scan.get_last_position()
        else:
            resume_at = 0.0
        last_pos = client.play(self.media_scan, resume_at=resume_at)
        self.config.restore_after_external_app()
        self.media_scan.set_last_position(last_pos)
    
    def get_metadata(self):
        return {
            'mmdb': self.config.mmdb.get(self.imdb_id),
            'media_scan': self.media_scan,
            'season': self.season,
            }


class RootMenu(MenuItem):
    def __init__(self, config):
        MenuItem.__init__(self, "Dinoteeth Media Launcher", theme=config.theme)
        self.config = config
        self.metadata = {
            'image': 'background-merged.jpg',
            }
        
        self.category_order = [
            ("Movies & Series", TopLevelLookup(self.config, [MovieMetadata, SeriesMetadata])),
            ("Just Movies", TopLevelLookup(self.config, [MovieMetadata])),
            ("Just Series", TopLevelLookup(self.config, [SeriesMetadata])),
            ("Paused...", self.get_empty_root),
            ("Games", self.get_empty_root),
            ]
        self.categories = {}
    
    def create_menus(self):
        for cat, populator in self.category_order:
            item = MenuItem(cat, populate_children=populator)
            self.add(item)
            if hasattr(populator, 'get_metadata'):
                item.metadata = populator.get_metadata()
        self.create_photo_menu()
    
    def create_movies_genres(self, *args):
        results = self.db.find("movie")
        menu = MenuItem("Movies")
        menu.metadata = {'imagegen': results.thumbnail_mosaic}
        self.add(menu)
        entry = MenuItem("All", populate=self.get_movies_root)
        entry.metadata = {'imagegen': results.thumbnail_mosaic}
        menu.add(entry)
        genres = sorted(list(results.all_metadata('genres')))
        for genre in genres:
            subset = results.subset_by_metadata('genres', genre)
            entry = MenuItem(genre, populate=subset.hierarchy)
            entry.metadata = {'imagegen': subset.thumbnail_mosaic}
            menu.add(entry)
    
    def create_photo_menu(self, *args):
        menu = MenuItem("Photos")
        #menu.metadata = {'imagegen': photodb.thumbnail_mosaic}
        self.add(menu)
        entry = MenuItem("By Folder", populate=self.config.pdb.hierarchy)
        #entry.metadata = {'imagegen': photodb.thumbnail_mosaic}
        menu.add(entry)
        entry = MenuItem("Slideshows")
        #entry.metadata = {'imagegen': results.thumbnail_mosaic}
        menu.add(entry)
    
    def get_empty_root(self, parent):
        raise StopIteration
    
    def save_state(self):
        pass
