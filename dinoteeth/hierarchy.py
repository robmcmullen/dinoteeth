import os, sys, glob, re, logging, time, calendar

from model import MenuItem, MenuPopulator
from metadata import MovieMetadata, SeriesMetadata
from photo import TopLevelPhoto
from updates import UpdateManager

logging.basicConfig(level=logging.WARNING)

log = logging.getLogger("dinoteeth.hierarchy")
log.setLevel(logging.DEBUG)

class MMDBPopulator(MenuPopulator):
    def get_sorted_metadata(self):
        metadata = list(self.media.get_unique_metadata())
        metadata.sort()
        return metadata
        
    def iter_image_path(self, artwork_loader):
        for metadata in self.get_sorted_metadata():
            imgpath = artwork_loader.get_poster_filename(metadata.id)
            if imgpath is not None:
                yield imgpath

class MetadataLookup(MMDBPopulator):
    def __init__(self, parent, config, filter=None):
        MMDBPopulator.__init__(self, config)
        self.parent = parent
        self.filter = filter
    
    def get_media(self):
        media = self.parent.get_media().filter(self.filter)
        return media
    
    media = property(get_media)
        
    def iter_create(self):
        metadata = self.get_sorted_metadata()
        for m in metadata:
            if m.media_category == "series":
                if m.is_mini_series():
                    yield unicode(m.title), SeriesEpisodes(self, self.config, m.id)
                else:
                    yield unicode(m.title), SeriesTopLevel(self, self.config, m.id)
            elif m.media_category == "movies":
                yield unicode(m.title), MovieTopLevel(self, self.config, m.id)
    
    def get_metadata(self):
        return {
            'imagegen': self.thumbnail_mosaic,
            }


def only_paused(item):
    if item.play_date is None:
        return False
    return item.is_paused()

def play_date(item):
    if item.play_date is None:
        return 0
    # Need to return unix timestamp
    return calendar.timegm(item.play_date.utctimetuple())


class TopLevelLookup(MetadataLookup):
    def iter_create(self):
        yield "All", MetadataLookup(self, self.config)
        yield "Recently Added", DateLookup(self, self.config)
        yield "Recently Played", DateLookup(self, self.config, filter=lambda item: item.play_date is not None, time_lookup=play_date)
        
        credit_map = MovieMetadata.credit_map
        for title, credit, limit, converter, reverse_sort in credit_map:
            yield title, CreditLookup(self, self.config, credit, converter, reverse_sort)

    def get_metadata(self):
        return {
            'imagegen': self.thumbnail_mosaic,
            'edit': EditTestRoot(self.config),
            }


class DateLookup(MetadataLookup):
    def __init__(self, parent, config, filter=None, time_lookup=None):
        MetadataLookup.__init__(self, parent, config, filter)
        if time_lookup is None:
            time_lookup = lambda item: item.metadata.date_added
        self.time_lookup = time_lookup
    
    def get_sorted_metadata(self):
        order = sorted([(v, m) for m, v in self.media.get_unique_metadata_with_value(self.time_lookup).iteritems()])
        metadata = [item[1] for item in reversed(order)]
        return metadata
        
    def iter_create(self):
        yield "Last Week", MetadataLookup(self, self.config, filter=lambda item: self.time_lookup(item) >= time.time() - 7*24*3600)
        yield "Last 2 Weeks", MetadataLookup(self, self.config, filter=lambda item: self.time_lookup(item) >= time.time() - 14*24*3600)
        yield "Last Month", MetadataLookup(self, self.config, filter=lambda item: self.time_lookup(item) >= time.time() - 31*24*3600)
        yield "Last 2 Months", MetadataLookup(self, self.config, filter=lambda item: self.time_lookup(item) >= time.time() - 62*24*3600)
        yield "Last 3 Months", MetadataLookup(self, self.config, filter=lambda item: self.time_lookup(item) >= time.time() - 93*24*3600)
        yield "Last 6 Months", MetadataLookup(self, self.config, filter=lambda item: self.time_lookup(item) >= time.time() - 182*24*3600)
        yield "Last Year", MetadataLookup(self, self.config, filter=lambda item: self.time_lookup(item) >= 365*24*3600)


class CreditLookup(MetadataLookup):
    def __init__(self, parent, config, credit=None, converter=None, reverse_sort=False):
        MetadataLookup.__init__(self, parent, config, None)
        self.credit = credit
        if converter is None:
            converter = lambda d: d
        self.converter = converter
        self.reverse_sort = reverse_sort
    
    def iter_create(self):
        results = {}
        for metadata in self.media.get_unique_metadata():
            if metadata.match(self.credit):
                for credit_value in metadata.iter_items_of(self.credit):
                    results[self.converter(credit_value)] = credit_value
        presorted = zip(results.values(), results.keys())
        presorted.sort()
        credits = [i[1] for i in presorted]
        if self.reverse_sort:
            credits.reverse()
        for credit in credits:
            if hasattr(credit, 'imdb_prefix'):
                name = unicode(credit)
            else:
                name = credit
            name = unicode(credit)
            
            # Have to rebind `credit` to a default argument rather than
            # simply
            #
            # lambda item: item.metadata.match(self.credit, credit,
            # self.converter)
            #
            # because the for loop rebinds the local variable during each
            # iteration and when the lambda function is eventually called
            # (well after this loop completes) all the lambdas point to the
            # last value when looking up `credit`
            yield name, MetadataLookup(self, self.config, filter=lambda item, value=credit: item.metadata.match(self.credit, value, self.converter))


class PlayableEntries(MetadataLookup):
    def __init__(self, parent, config, imdb_id):
        self.imdb_id = imdb_id
        MetadataLookup.__init__(self, parent, config, filter=lambda item: item.metadata.id == imdb_id)
    
    def __call__(self, parent):
        items = []
        for title, playable in self.iter_create():
            items.append((title, playable))
        if self.autosort:
            items.sort()
        for title, playable in items:
            item = MenuItem(title, action=playable.play, metadata=playable.get_metadata())
            yield item
    
    def get_resume_entry(self, m, season=None):
        return "  Resume (Paused at %s)" % m.paused_at_text(), MediaPlay(self.config, self.imdb_id, m, season=season, resume=True)


class MovieTopLevel(PlayableEntries):
    def iter_create(self):
        media_scans = self.get_media()
        media_scans.sort()
        bonus = media_scans.get_bonus()
        found_bonus = False
        for m in media_scans:
            if not found_bonus and m.is_bonus() and len(bonus) > 1:
                yield "Play All Bonus Features", MediaPlayMultiple(self.config, self.imdb_id, bonus)
                found_bonus = True
            yield unicode(m.display_title), MediaPlay(self.config, self.imdb_id, m)
            if m.is_paused():
                yield self.get_resume_entry(m)
                
    
    def get_metadata(self):
        return {
            'mmdb': self.config.db.get_metadata(self.imdb_id),
            'edit': ChangeImdbRoot(self.config, self.imdb_id),
            }


class SeriesTopLevel(MetadataLookup):
    def __init__(self, parent, config, imdb_id):
        self.imdb_id = imdb_id
        MetadataLookup.__init__(self, parent, config, filter=lambda item: item.metadata.id == imdb_id)
        
    def iter_create(self):
        media_scans = self.get_media()
        seasons = media_scans.get_seasons()
        for s in seasons:
            yield u"Season %d" % s, SeriesEpisodes(self, self.config, self.imdb_id, s)
    
    def get_metadata(self):
        return {
            'mmdb': self.config.db.get_metadata(self.imdb_id),
            'edit': ChangeImdbRoot(self.config, self.imdb_id),
            }


class SeriesEpisodes(PlayableEntries):
    def __init__(self, parent, config, imdb_id, season=0):
        PlayableEntries.__init__(self, parent, config, imdb_id)
        self.season = season
        
    def iter_create(self):
        media_scans = self.get_media()
        episodes = media_scans.get_episodes(self.season)
        bonus = [m for m in episodes if m.is_bonus()]
        found_bonus = False
        for m in episodes:
            if not found_bonus and m.is_bonus() and len(bonus) > 1:
                yield "Play All Bonus Features", MediaPlayMultiple(self.config, self.imdb_id, bonus)
                found_bonus = True
            yield unicode(m.display_title), MediaPlay(self.config, self.imdb_id, m, season=self.season)
            if m.is_paused():
                yield self.get_resume_entry(m, self.season)

    def get_metadata(self):
        return {
            'mmdb': self.config.db.get_metadata(self.imdb_id),
            'season': self.season,
            'edit': ChangeImdbRoot(self.config, self.imdb_id),
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
        self.media_scan.set_last_position(last_pos)
        self.config.restore_after_external_app()
    
    def get_metadata(self):
        return {
            'mmdb': self.config.db.get_metadata(self.imdb_id),
            'media_scan': self.media_scan,
            'season': self.season,
            }

class MediaPlayMultiple(MMDBPopulator):
    def __init__(self, config, imdb_id, media_scans, season=None, resume=False):
        MMDBPopulator.__init__(self, config)
        self.imdb_id = imdb_id
        self.media_scans = media_scans
        self.season = season
        self.resume = resume
        
    def play(self, config=None):
        self.config.prepare_for_external_app()
        client = self.config.get_media_client()
        for m in self.media_scans:
            if self.resume:
                resume_at = m.get_last_position()
            else:
                resume_at = 0.0
            last_pos = client.play(m)
            m.set_last_position(last_pos)
            if not m.is_considered_complete(last_pos):
                # Stop the playlist if the user quits in the middle of playback
                break
        self.config.restore_after_external_app()
    
    def get_metadata(self):
        return {
            'mmdb': self.config.db.get_metadata(self.imdb_id),
            'season': self.season,
            }


class ChangeImdbRoot(MenuPopulator):
    def __init__(self, config, imdb_id):
        MenuPopulator.__init__(self, config)
        self.imdb_id = imdb_id
        self.root_title = "Change Title Lookup"
        
    def iter_create(self):
        media_scans = self.config.db.get_all_with_imdb_id(self.imdb_id)
        if len(media_scans) > 0:
            title_key = media_scans[0].title_key
            imdb_guesses = self.config.mmdb.guess(title_key[0], year=title_key[1], find=title_key[2])
            for result in imdb_guesses:
                yield result['title'], ChangeImdb(self.config, title_key, result)

class ChangeImdb(MenuPopulator):
    def __init__(self, config, title_key, imdb_search_result):
        MenuPopulator.__init__(self, config)
        self.title_key = title_key
        self.imdb_search_result = imdb_search_result
        
    def play(self, config=None):
        status = "Selected %s" % self.imdb_search_result['smart long imdb canonical title']
        self.config.db.change_imdb_id(self.title_key, self.imdb_search_result.imdb_id, self.config.mmdb)
        UpdateManager.update_all_posters()
        self.config.show_status(status)
    
    def get_metadata(self):
        return {
            'imdb_search_result': self.imdb_search_result
            }


class EditTestRoot(MenuPopulator):
    def __init__(self, config):
        MenuPopulator.__init__(self, config)
        self.root_title = "Edit Test!"
        
    def iter_create(self):
        for name in ["test entry %d" % i for i in range(10)]:
            test_id = name
            yield name, EditTest(self.config, test_id)

class EditTest(MenuPopulator):
    def __init__(self, config, test_id):
        MenuPopulator.__init__(self, config)
        self.test_id = test_id
        
    def play(self, config=None):
        status = "Selected %s" % self.test_id
        self.config.show_status(status)


class RootPopulator(MMDBPopulator):
    def __init__(self, config):
        MenuPopulator.__init__(self, config)
        self.root_title = "Dinoteeth Media Launcher"
        self.media_cache = None
    
    def get_media(self):
        if self.media_cache is None:
            self.media_cache = self.config.db.get_all()
        return self.media_cache
    
    media = property(get_media)
        
    def iter_create(self):
        yield "Movies & Series", TopLevelLookup(self, self.config)
        yield "Just Movies", TopLevelLookup(self, self.config, lambda scan: scan.type == "movie")
        yield "Just Series", TopLevelLookup(self, self.config, lambda scan: scan.type == "series")
        yield "Paused...", DateLookup(self, self.config, filter=only_paused, time_lookup=play_date)
        yield "Photos & Home Videos", TopLevelPhoto(self.config)
        yield "Games", TopLevelLookup(self, self.config)

    def get_metadata(self):
        return {
            'image': 'background-merged.jpg',
            }

def RootMenu(config):
    return MenuItem.create_root(RootPopulator(config))
