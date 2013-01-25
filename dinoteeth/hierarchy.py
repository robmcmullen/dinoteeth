import os, sys, glob, re, logging, time, calendar

from model import MenuItem, MenuPopulator
import settings
from photo import TopLevelPhoto
from metadata import MetadataLoader, BaseMetadata
from utils import TitleKey
from database import StaticFileList

log = logging.getLogger("dinoteeth.hierarchy")


class MMDBPopulator(MenuPopulator):
    def __init__(self, config):
        MenuPopulator.__init__(self, config)
        self.cached_media = None
    
    def get_media(self):
        return StaticFileList()
    
    def get_cached_media(self):
        if self.cached_media is None or True:
            log.debug("start: getting media for %s" % self.__class__.__name__)
            self.cached_media = self.get_media()
            log.debug("finish: getting media for %s" % self.__class__.__name__)
        return self.cached_media
    
    media = property(get_cached_media)
        
    def get_search_populator(self, text):
        return SearchPopulator(self, self.config, text)
    
    def get_sorted_metadata(self):
        unique, scans_in_each = self.media.get_unique_metadata()
        metadata = list(unique)
        metadata.sort()
        return metadata
        
    def iter_image_path(self):
        for metadata in self.get_sorted_metadata():
            try:
                loader = MetadataLoader.get_loader(metadata)
                imgpath = loader.get_poster(metadata)
                if imgpath is not None:
                    yield imgpath
            except RuntimeError:
                print "No loader for %s" % str(metadata)

class MetadataLookup(MMDBPopulator):
    def __init__(self, parent, config, filter=None):
        MMDBPopulator.__init__(self, config)
        self.parent = parent
        self.filter = filter
    
    def get_media(self):
        media = self.parent.get_media().filter(self.filter)
        return media
        
    def iter_create(self):
        metadata = self.get_sorted_metadata()
        for m in metadata:
            if m.media_category == "video":
                if m.media_subcategory == "series":
                    if m.is_mini_series():
                        yield unicode(m.title), SeriesEpisodes(self, self.config, m)
                    else:
                        yield unicode(m.title), SeriesTopLevel(self, self.config, m)
                elif m.media_subcategory == "movies":
                    yield unicode(m.title), MovieTopLevel(self, self.config, m)
            elif m.media_category == "game":
                yield unicode(m.title), GameDetails(self, self.config, m)
    
    def get_metadata(self):
        return {
            'imagegen': self.thumbnail_mosaic,
            }


class SearchPopulator(MetadataLookup):
    def __init__(self, parent, config, initial_text=""):
        MetadataLookup.__init__(self, parent, config)
        self.set_search_text(initial_text)
        
    def set_search_text(self, text):
        self.root_title = "Search: %s_" % text
        text = text.lower()
        print "search text: -->%s<--" % text
        self.filter = lambda f: text in f.metadata.title.lower()


def only_paused(item):
    if item.scan.play_date is None:
        return False
    return item.scan.is_paused()

def play_date(item):
    if item.scan.play_date is None:
        return 0
    # Need to return unix timestamp
    return calendar.timegm(item.scan.play_date.utctimetuple())


class TopLevelLookup(MetadataLookup):
    def iter_create(self):
        yield "All", MetadataLookup(self, self.config)
        yield "Favorites", MetadataLookup(self, self.config, filter=lambda f: f.metadata.starred)
        yield "Recently Added", DateLookup(self, self.config)
        yield "Recently Played", DateLookup(self, self.config, filter=lambda f: f.scan.play_date is not None, time_lookup=play_date)
        
        for title, credit_entry in self.iter_credit():
            yield title, credit_entry
    
    def iter_credit(self):
        raise StopIteration

    def get_metadata(self):
        return {
            'imagegen': self.thumbnail_mosaic,
            'edit_metadata': EditTestRoot(self.config),
            }


class TopLevelVideos(TopLevelLookup):
    def get_media(self):
        return self.config.db.get_all("video").filter(self.filter)

    def iter_credit(self):
        for title, credit, limit, converter, reverse_sort in settings.credit_map:
            yield title, CreditLookup(self, self.config, credit, converter, reverse_sort)


class TopLevelGames(TopLevelLookup):
    def get_media(self):
        return self.config.db.get_all("game").filter(self.filter)



class DateLookup(MetadataLookup):
    def __init__(self, parent, config, filter=None, time_lookup=None):
        MetadataLookup.__init__(self, parent, config, filter)
        if time_lookup is None:
            time_lookup = lambda f: f.metadata.date_added
        self.time_lookup = time_lookup
    
    def get_sorted_metadata(self):
        unique, scans_in_each = self.media.get_unique_metadata_with_value(self.time_lookup)
        order = sorted([(v, m) for m, v in unique.iteritems()])
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
        unique, scans_in_earch = self.media.get_unique_metadata()
        for metadata in unique:
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
            # lambda f: f.metadata.match(self.credit, credit,
            # self.converter)
            #
            # because the for loop rebinds the local variable during each
            # iteration and when the lambda function is eventually called
            # (well after this loop completes) all the lambdas point to the
            # last value when looking up `credit`
            yield name, MetadataLookup(self, self.config, filter=lambda item, value=credit: item.metadata.match(self.credit, value, self.converter))


class PlayableEntries(MetadataLookup):
    def __init__(self, parent, config, metadata):
        self.metadata = metadata
        MetadataLookup.__init__(self, parent, config, filter=lambda f: f.metadata.id == self.metadata.id)
    
    def __call__(self, parent):
        items = []
        for title, playable in self.iter_create():
            items.append((title, playable))
        if self.autosort:
            items.sort()
        for title, playable in items:
            item = MenuItem(title, action=playable.play, metadata=playable.get_metadata())
            yield item
    
    def get_resume_entry(self, media_file, season=None):
        return "  Resume (Paused at %s)" % media_file.scan.paused_at_text(), MediaPlay(self.config, self.metadata, media_file, season=season, resume=True)


class MovieTopLevel(PlayableEntries):
    def iter_create(self):
        media_files = self.get_media().static_list()
        media_files.sort()
        print media_files
        
        bonus = media_files.get_bonus()
        found_bonus = False
        for f in media_files:
            if not found_bonus and f.scan.is_bonus and len(bonus) > 1:
                yield "Play All Bonus Features", MediaPlayMultiple(self.config, self.metadata, bonus)
                found_bonus = True
            yield unicode(f.scan.display_title), MediaPlay(self.config, self.metadata, f)
            if f.scan.is_paused():
                yield self.get_resume_entry(f)
                
    
    def get_metadata(self):
        return {
            'mmdb': self.metadata,
            'edit_metadata': ChangeImdbRoot(self, self.config, self.metadata),
            'edit_poster': ChangePosterRoot(self, self.config, self.metadata),
            }


class SeriesTopLevel(MetadataLookup):
    def __init__(self, parent, config, metadata):
        self.metadata = metadata
        MetadataLookup.__init__(self, parent, config, filter=lambda f: f.metadata.id == self.metadata.id)
        
    def iter_create(self):
        media_files = self.get_media()
        seasons = media_files.get_seasons()
        for s in seasons:
            yield u"Season %d" % s, SeriesEpisodes(self, self.config, self.metadata, s)
    
    def get_metadata(self):
        return {
            'mmdb': self.metadata,
            'edit_metadata': ChangeImdbRoot(self, self.config, self.metadata),
            'edit_poster': ChangePosterRoot(self, self.config, self.metadata),
            }


class SeriesEpisodes(PlayableEntries):
    def __init__(self, parent, config, metadata, season=0):
        PlayableEntries.__init__(self, parent, config, metadata)
        self.season = season
        
    def iter_create(self):
        media_files = self.get_media()
        episodes = media_files.get_episodes(self.season)
        bonus = [f for f in episodes if f.scan.is_bonus]
        found_bonus = False
        for f in episodes:
            if not found_bonus and f.scan.is_bonus and len(bonus) > 1:
                yield "Play All Bonus Features", MediaPlayMultiple(self.config, self.metadata, bonus)
                found_bonus = True
            yield unicode(f.scan.display_title), MediaPlay(self.config, self.metadata, f, season=self.season)
            if f.scan.is_paused():
                yield self.get_resume_entry(f, self.season)

    def get_metadata(self):
        return {
            'mmdb': self.metadata,
            'season': self.season,
            'edit_metadata': ChangeImdbRoot(self, self.config, self.metadata),
            'edit_poster': ChangePosterRoot(self, self.config, self.metadata, season=self.season),
            }


class GameDetails(PlayableEntries):
    def __init__(self, parent, config, metadata, season=0):
        PlayableEntries.__init__(self, parent, config, metadata)
        self.season = season
        
    def iter_create(self):
        media_files = self.get_media()
        media_files.sort()
        for f in media_files:
            yield unicode(self.metadata.title), MediaPlay(self.config, self.metadata, f)
            if f.scan.has_saved_games():
                for saved in f.get_saved_games():
                    yield self.get_saved_game_entry(f, saved)
    
    def get_saved_game_entry(self, media_file, saved):
        return "  Resume (Paused at %s)" % media_file.scan.paused_at_text(), MediaPlay(self.config, self.metadata, media_file, resume=True, resume_data=saved)

    def get_metadata(self):
        return {
            'mmdb': self.metadata,
            'edit_metadata': ChangeImdbRoot(self, self.config, self.metadata),
            'edit_poster': ChangePosterRoot(self, self.config, self.metadata),
            }


class MediaPlay(MMDBPopulator):
    def __init__(self, config, metadata, media_file, season=None, resume=False, resume_data=None):
        MMDBPopulator.__init__(self, config)
        self.metadata = metadata
        self.media_file = media_file
        self.season = season
        self.resume = resume
        self.resume_data = resume_data
        
    def play(self, config=None):
        self.config.prepare_for_external_app()
        client = self.config.get_media_client(self.media_file)
        if self.resume:
            resume_at = self.media_file.scan.get_last_position()
        else:
            resume_at = 0.0
        last_pos = client.play(self.media_file, resume_at=resume_at, resume_data=self.resume_data)
        self.media_file.scan.set_last_position(last_pos)
        self.config.restore_after_external_app()
    
    def get_metadata(self):
        return {
            'mmdb': self.metadata,
            'media_file': self.media_file,
            'season': self.season,
            }

class MediaPlayMultiple(MMDBPopulator):
    def __init__(self, config, metadata, media_files, season=None, resume=False):
        MMDBPopulator.__init__(self, config)
        self.metadata = metadata
        self.media_files = media_files
        self.season = season
        self.resume = resume
        
    def play(self, config=None):
        self.config.prepare_for_external_app()
        client = self.config.get_media_client(self.media_file)
        for f in self.media_files:
            if self.resume:
                resume_at = f.scan.get_last_position()
            else:
                resume_at = 0.0
            last_pos = client.play(f)
            f.scan.set_last_position(last_pos)
            if not f.scan.is_considered_complete(last_pos):
                # Stop the playlist if the user quits in the middle of playback
                break
        self.config.restore_after_external_app()
    
    def get_metadata(self):
        return {
            'mmdb': self.metadata,
            'season': self.season,
            }


class ExpandedLookup(MetadataLookup):
    indent = u"      "
    
    def __init__(self, parent, config, filter=None, time_lookup=None):
        MetadataLookup.__init__(self, parent, config, filter)
        if time_lookup is None:
            time_lookup = lambda f: f.metadata.date_added
        self.time_lookup = time_lookup
    
    def get_sorted_metadata(self):
        metadata, scans_in_each = self.get_sorted_metadata_plus_scans()
        return metadata
    
    def get_sorted_metadata_plus_scans(self):
        unique, scans_in_each = self.media.get_unique_metadata_with_value(self.time_lookup)
        order = sorted([(v, m) for m, v in unique.iteritems()])
        metadata = [item[1] for item in reversed(order)]
        return metadata, scans_in_each
        
    def iter_create(self):
        metadata, scans_in_each = self.get_sorted_metadata_plus_scans()
        for m in metadata:
            media_files = scans_in_each[m]
            if m.media_subcategory == "series":
                if m.is_mini_series():
                    yield self.indent + unicode(m.title), None
                    yield unicode(m.title), SeriesEpisodes(self, self.config, m.id)
                else:
                    seasons = media_files.get_seasons()
                    for s in seasons:
                        yield self.indent + u"%s - Season %d" % (unicode(m.title), s), None
                        episodes = media_files.get_episodes(s)
                        for f in episodes:
                            yield "Resume %s (Paused at %s)" % (unicode(f.scan.display_title), f.scan.paused_at_text()), MediaPlay(self.config, m, f, resume=True)
            elif m.media_subcategory == "movies":
                yield self.indent + unicode(m.title), None
                media_files.sort()
                bonus = media_files.get_bonus()
                for f in media_files:
                    yield "Resume %s (Paused at %s)" % (unicode(f.scan.display_title), f.scan.paused_at_text()), MediaPlay(self.config, m, f, resume=True)


class ChangeImdbRoot(MetadataLookup):
    def __init__(self, parent, config, metadata):
        MetadataLookup.__init__(self, parent, config, filter=lambda f: f.metadata.id == metadata.id)
        self.metadata = metadata
        self.root_title = "Change Title Lookup"
        
    def iter_create(self):
        media_files = list(self.get_media())
        if len(media_files) > 0:
            title_key = media_files[0].scan.title_key
            loader = MetadataLoader.get_loader(self.metadata)
            guesses = loader.search(title_key)
            for result in guesses:
                yield result['title'], ChangeImdb(self, self.config, result, title_key)
#                print result
#                print dir(result)
#                print result.summary().encode('utf-8')

class ChangeImdb(MMDBPopulator):
    def __init__(self, parent, config, result, orig_title_key):
        MMDBPopulator.__init__(self, config)
        self.parent = parent
        self.result = result
        self.title_key = TitleKey(orig_title_key.category, orig_title_key.subcategory, result['title'], result['year'])
        self.loader = MetadataLoader.get_loader(self.title_key)
        self.metadata = self.loader.get_basic_metadata(self.title_key, self.result)
        self.first_time = True
    
    def on_selected_item(self):
        """Callback to trigger something when the cursor is on the menu item"""
        print "Drawing %s: %s" % (self.result.imdb_id, self.result['title'].encode('utf-8'))
        if self.first_time:
            self.loader.get_poster_background(self.metadata)
            self.first_time = False
        
    def play(self, config=None):
        status = "Selected %s" % self.result['smart long imdb canonical title'].encode('utf-8')
        metadata = self.loader.get_metadata_by_id(self.result.imdb_id)
        metadata.merge_database_objects(self.config.db)
        self.config.db.zodb.commit()
        media_files = self.parent.get_media()
        self.config.db.change_metadata(media_files, metadata.id)
        self.config.show_status(status)
    
    def get_metadata(self):
        return {
            'imdb_search_result': self.result,
            'metadata': self.metadata,
            }


class ChangePosterRoot(MetadataLookup):
    def __init__(self, parent, config, metadata, season=None):
        MetadataLookup.__init__(self, parent, config, filter=lambda f: f.metadata.id == metadata.id)
        self.metadata = metadata
        self.root_title = "Change Poster"
        
    def iter_create(self):
        loader = MetadataLoader.get_loader(self.metadata)
        posters = loader.get_known_posters(self.metadata)
        if len(posters) > 0:
            for url, path in posters:
                yield os.path.basename(path), ChangePoster(self, self.config, self.metadata, url, path)
#                print result
#                print dir(result)
#                print result.summary().encode('utf-8')

class ChangePoster(MMDBPopulator):
    def __init__(self, parent, config, metadata, url, path):
        MMDBPopulator.__init__(self, config)
        self.url = url
        self.path = path
        self.metadata = metadata
        self.first_time = True
    
    def on_selected_item(self):
        """Callback to trigger something when the cursor is on the menu item"""
        print "Drawing %s: %s" % (self.metadata.id, self.path)
        if self.first_time:
            #self.loader.get_poster_background(self.metadata)
            self.first_time = False
        
    def play(self, config=None):
        status = "Selected %s" % self.path
        loader = MetadataLoader.get_loader(self.metadata)
        with open(self.path) as fh:
            data = fh.read()
        loader.save_poster(self.metadata, self.url, data)
        self.config.show_status(status)
    
    def get_metadata(self):
        return {
            'metadata': self.metadata,
            'poster_path': self.path,
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
        
    def get_media(self):
        return self.config.db.get_all("all")

    def iter_create(self):
        yield "Movies & Series", TopLevelVideos(self, self.config)
        yield "Just Movies", TopLevelVideos(self, self.config, lambda f: f.scan.subcat == "movie")
        yield "Just Series", TopLevelVideos(self, self.config, lambda f: f.scan.subcat == "series")
        yield "Favorites", MetadataLookup(self, self.config, filter=lambda f: f.metadata and f.metadata.starred)
        yield "Paused", ExpandedLookup(self, self.config, filter=only_paused, time_lookup=play_date)
        yield "Photos & Home Videos", TopLevelPhoto(self.config)
        yield "Games", TopLevelGames(self, self.config)

    def get_metadata(self):
        return {
            'image': 'background-merged.jpg',
            }

class TestMenuPopulator(MetadataLookup):
    def __init__(self, config, match):
        MetadataLookup.__init__(self, self, config, lambda f: match in f.metadata.title)
        self.root_title = "Dinoteeth Testing: match %s" % match
        
    def get_media(self):
        stuff = self.config.db.get_all("all").filter(self.filter)
        print stuff
        return stuff
    
    def iter_create(self):
        media_files = self.get_media()
        metadata = list(set([f.metadata for f in media_files]))
        for m in metadata:
            if m.media_category == "video":
                if m.media_subcategory == "series":
                    if m.is_mini_series():
                        pop = SeriesEpisodes(self, self.config, m)
                    else:
                        pop = SeriesTopLevel(self, self.config, m)
                elif m.media_subcategory == "movies":
                    pop = MovieTopLevel(self, self.config, m)
            elif m.media_category == "game":
                pop = GameDetails(self, self.config, m)
            
            for item in pop.iter_create():
                yield item

def RootMenu(config):
    if config.options.test_menu:
        return MenuItem.create_root(TestMenuPopulator(config, config.options.test_menu))
    else:
        return MenuItem.create_root(RootPopulator(config))
