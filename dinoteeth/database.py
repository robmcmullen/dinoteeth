import os, time, collections, logging

import transaction

from utils import iter_dir
from filescan import MediaFile
from metadata import MetadataLoader

log = logging.getLogger("dinoteeth.database")
log.setLevel(logging.DEBUG)


class StaticFileList(list):
    def __str__(self):
        lines = []
        for item in self:
            lines.append("FileScan -> %s" % item.pathname)
            lines.append("  title_key: %s" % str(item.scan.title_key))
            lines.append("  metadata: %s" % item.metadata)
        return "\n".join(lines)
        
    def get_seasons(self):
        seasons = set()
        for m in self:
            seasons.add(m.scan.season)
        seasons = list(seasons)
        seasons.sort()
        return seasons
    
    def get_episodes(self, season_number):
        episodes = []
        for m in self:
            if m.scan.season == season_number:
                episodes.append(m)
        episodes.sort()
        return episodes
    
    def get_bonus(self, season_number=-1):
        bonus = []
        for m in self:
            if (season_number < 0 or m.scan.season == season_number) and m.scan.is_bonus:
                bonus.append(m)
        bonus.sort()
        return bonus
    
    def get_total_runtime(self):
        """Return best guess for runtime of main feature, or total time
        of episodes (ignoring bonus features)
        
        @returns: (tuple) time in minutes, number of episodes
        """
        runtimes = []
        for m in self:
            if not m.scan.is_bonus:
                runtimes.append(m.scan.length / 60.0)
        runtimes.sort()
        
        # Handle pathological case
        if len(runtimes) == 0:
            return (0, 1)
        
        # Throw out largest and smallest, replace with median
        print "get_total_runtime: %s: before=%s" % (m.scan.title, runtimes)
        num = len(runtimes)
        if num > 4:
            median = runtimes[num/2]
            runtimes[0] = median
            runtimes[-1] = median
        print "get_total_runtime: %s: after median=%s" % (m.scan.title, runtimes)
        return reduce(lambda a,b: a+b, runtimes), num
    
    def get_main_feature(self):
        non_bonus = []
        for m in self:
            if not m.scan.is_bonus:
                non_bonus.append((m.scan.length, m))
        non_bonus.sort()
        try:
            return non_bonus[0][1]
        except:
            return None
    
    def get_unique_metadata(self):
        s = set()
        scans_in_each = dict()
        for item in self:
            s.add(item.metadata)
            if item.metadata not in scans_in_each:
                scans_in_each[item.metadata] = FilteredFileList()
            scans_in_each[item.metadata].append(item)
        return s, scans_in_each
    
    def get_unique_metadata_with_value(self, accessor):
        s = dict()
        scans_in_each = dict()
        for item in self:
            value = accessor(item)
            if item.metadata not in s or value > s[item.metadata]:
                s[item.metadata] = value
            if item.metadata not in scans_in_each:
                scans_in_each[item.metadata] = FilteredFileList()
            scans_in_each[item.metadata].append(item)
        return s, scans_in_each
    
class FilteredFileList(StaticFileList):
    def __init__(self, parent=None, filter_callable=None, *args, **kwargs):
        list.__init__(self, *args, **kwargs)
        self.parent = parent
        if filter_callable is None:
            filter_callable = lambda x: True
        self.filter_callable = filter_callable
        
    def filter(self, criteria):
        filtered = FilteredFileList(parent=self, filter_callable=criteria)
        return filtered
    
    def static_list(self):
        slist = StaticFileList()
        for item in self:
            slist.append(item)
        return slist
    
    def __iter__(self):
        if self.parent is None:
            index = 0
            while True:
                try:
                    item = self[index]
                    if self.filter_callable(item):
                        yield item
                except IndexError:
                    raise StopIteration
                index += 1
        else:
            for item in self.parent:
                if self.filter_callable(item):
                    yield item
    
    def __len__(self):
        if self.parent is None:
            return list.__len__(self)
        else:
            count = 0
            for item in self:
                count += 1
            return count


class HomeTheaterDatabase(object):
    def __init__(self, zodb):
        self.zodb = zodb
        self.scans = zodb.get_mapping("scans")
        self.metadata = zodb.get_mapping("metadata")
        self.title_key_to_metadata = zodb.get_mapping("title_key_to_metadata")
        self.zodb_title_key_map = zodb.get_mapping("title_key_map")
    
    def pack(self):
        self.zodb.pack()
    
    def get_all(self, category):
        self.zodb.sync()
        media_files = FilteredFileList()
        for media_file in self.scans.itervalues():
            scan = media_file.scan
            if scan is not None and (category == "all" or scan.category == category):
                media_files.append(media_file)
        log.debug("Last modified: %s, # scans=%d" % (self.zodb.get_last_modified(), len(media_files)))
        return media_files
    
    def get(self, pathname):
        return self.scans[pathname]
    
    def get_metadata(self, imdb_id):
        return self.metadata.get(imdb_id, None)
    
    def add(self, pathname, flags=""):
        media_file = MediaFile(pathname, flags=flags)
        self.scans[media_file.pathname] = media_file
        return media_file
    
    def change_metadata(self, media_files, imdb_id):
        metadata = self.get_metadata(imdb_id)
        if metadata is None:
            log.error("Metadata for %s must be stored in database before changing media files' metadata" % imdb_id)
        
        # Find all title keys referenced by the scans
        title_keys = set()
        for item in media_files:
            title_keys.add(item.scan.title_key)
        
        # Reset title key lookup to use new metadata
        for title_key in title_keys:
            self.title_key_to_metadata[title_key] = metadata
            scans = FilteredFileList(self.title_key_map[title_key])
            for item in scans:
                log.debug("Changing metadata for %s" % item.pathname)
                item.metadata = metadata
                metadata.update_with_media_files(scans)
        self.zodb.commit()
    
    def is_current(self, pathname, found_keys=None):
        if pathname in self.scans:
            if found_keys is not None:
                found_keys.add(pathname)
            media_file = self.scans[pathname]
            return media_file.is_current()
        return False
    
    def scan_files(self, path_iterable, flags, found_keys=None):
        """Scan files from an iterable object and add them to the database
        """
        for pathname in path_iterable:
            if not self.is_current(pathname, found_keys=found_keys):
                media_file = self.add(pathname, flags)
#                log.debug("added: %s" % self.get(media_file.pathname))
                log.debug("added: %s" % media_file)
        
    def scan_dirs(self, media_path_dict, valid_extensions=None):
        stored_keys = set(self.scans.keys())
        current_keys = set()
        for path, flags in media_path_dict.iteritems():
            print "Parsing path %s" % path
            dir_iterator = iter_dir(path, valid_extensions)
            self.scan_files(dir_iterator, flags, current_keys)
        removed_keys = stored_keys - current_keys
        for key in removed_keys:
            print "Removing %s" % key
            del self.scans[key]
        self.zodb.commit()
    
    def update_metadata(self):
        self.create_title_key_map()
        self.update_metadata_map()
        self.zodb.set_last_modified()
        self.zodb.commit()
    
    def scan_and_update(self, media_path_dict, valid_extensions=None):
        self.scan_dirs(media_path_dict, valid_extensions)
        self.update_metadata()
    
    def create_title_key_map(self):
        t = self.zodb.get_mapping("title_key_map", clear=True)
        for path, item in self.scans.iteritems():
            if item.scan and hasattr(item.scan, 'title_key'):
                key = item.scan.title_key
                if key not in t:
                    t[key] = list()
                t[key].append(item)
        transaction.savepoint()
    
    def get_title_key_map(self):
        t = self.zodb.get_mapping("title_key_map")
        if not t:
            self.create_title_key_map()
            self.zodb.commit()
        return t
    
    title_key_map = property(get_title_key_map)
    
    def iter_title_key_map(self):
        for t, scans in self.title_key_map.iteritems():
            scans = FilteredFileList(scans)
            yield t, scans
    
    def update_metadata_map(self):
        t = self.zodb.get_mapping("title_key_to_metadata")
        for title_key, scans in self.iter_title_key_map():
            metadata = t.get(title_key, None)
            if metadata is None:
                loader = MetadataLoader.get_loader(title_key)
                metadata = loader.best_guess(title_key, scans)
                if metadata is None:
                    continue
                self.title_key_to_metadata[title_key] = metadata
            for item in scans:
                item.metadata = metadata
            metadata.update_with_media_files(scans)
            metadata.merge_database_objects(self)
            
        # Help for debugging a recursion error in zodb
        if False:
            for title_key, metadata in self.title_key_to_metadata.iteritems():
                print "%s: %s" % (title_key, metadata)
                import pprint
                print metadata.__class__
                from persistent import Persistent
                from persistent.wref import WeakRefMarker, WeakRef
                print isinstance(metadata, (Persistent, type, WeakRef))
                oid = metadata._p_oid
                print oid
                pprint.pprint(vars(metadata))
        transaction.savepoint()
    
    def title_keys_with_metadata(self):
        t = self.zodb.get_mapping("title_key_to_metadata")
        known_keys = set(t.keys())
        current_keys = set(self.title_key_map.keys())
        valid_keys = current_keys.intersection(known_keys)
        for key in valid_keys:
            yield key, t[key]

    def update_posters(self):
        for title_key, metadata in self.title_keys_with_metadata():
            loader = MetadataLoader.get_loader(title_key)
            if loader.has_poster(metadata):
                log.debug("Have poster for %s" % unicode(metadata).encode('utf-8'))
            else:
                log.debug("Loading poster for %s" % unicode(metadata).encode('utf-8'))
                loader.fetch_posters(metadata)
