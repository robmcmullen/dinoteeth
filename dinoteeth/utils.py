import os, sys, glob, logging, re
from datetime import datetime, timedelta

from persistent import Persistent

log = logging.getLogger("dinoteeth.utils")

from ZEO import ClientStorage
from ZODB import DB, FileStorage
import transaction
from persistent.mapping import PersistentMapping


class DBFacade(object):
    def __init__(self, path, host=""):
        if host:
            addr = host.split(":")
            addr = addr[0], int(addr[1])
            self.storage = ClientStorage.ClientStorage(addr, wait=False)
        else:
            self.storage = FileStorage.FileStorage(path)
        try:
            self.db = DB(self.storage)
            self.connection = self.db.open()
            self.dbroot = self.connection.root()
        except Exception, e:
            raise RuntimeError("Error connecting to dinoteeth database at %s" % str(addr))
    
    def get_unique_id(self):
        id = self.get_value("unique_counter", 0)
        id -= 1
        self.set_value("unique_counter", id)
        return id
    
    def add(self, name, obj):
        self.dbroot[name] = obj
    
    def get_mapping(self, name, clear=False):
        if name not in self.dbroot:
            self.dbroot[name] = PersistentMapping()
        if clear:
            self.dbroot[name].clear()
        return self.dbroot[name]
    
    def get_value(self, name, initial):
        if name not in self.dbroot:
            self.dbroot[name] = initial
        return self.dbroot[name]
    
    def set_value(self, name, value):
        self.dbroot[name] = value
    
    def add(self, name, obj):
        self.dbroot[name] = obj
    
    callbacks = []
    @classmethod
    def add_commit_callback(cls, callback):
        cls.callbacks.append(callback)
        
    @classmethod
    def commit(cls):
        transaction.commit()
        for callback in cls.callbacks:
            callback()
    
    def rollback(self):
        transaction.rollback()
    
    def abort(self):
        transaction.abort()
    
    def get_last_modified(self):
        return self.get_value("last_modified", -1)
    
    def set_last_modified(self):
        self.set_value("last_modified", time.time())
    
    def sync(self):
        self.connection.sync()
    
    def pack(self):
        self.db.pack()

    def close(self):
        self.connection.close()
        self.db.close()
        self.storage.close()


class TitleKey(Persistent):
    def __init__(self, category, subcategory, title, year):
        self.category = category
        self.subcategory = subcategory
        self.title = title
        self.year = year

    def __str__(self):
        return str(self.__dict__)

    def __hash__(self): 
        return hash((self.category, self.subcategory, self.title, self.year))

    def __eq__(self, other): 
        return self.__dict__ == other.__dict__

def decode_title_text(text):
    return text.replace('_n_',' & ').replace('-s_','\'s ').replace('-t_','\'t ').replace('-m_','\'m ').replace('.._',': ').replace('.,_','; ').replace('_',' ')

def encode_title_text(text):
    return text.replace(' & ','_n_').replace('\'s ','-s_').replace('\'t ','-t_').replace('\'m ','-m_').replace(': ','.._').replace('; ','.,_').replace(' ','_')

def shell_escape_path(path):
    escape_chars = [' ', '&', '(', ')']
    escaped_path = path
    for c in escape_chars: escaped_path = escaped_path.replace(c, "\\"+c)
    return escaped_path

def time_format(seconds):
    m, s = divmod(seconds, 60)
    h, m = divmod(m, 60)
    return "%d:%02d:%02d" % (h, m, s)

def time_since(d, now=None):
    """Fuzzy date printer, adapted from:
    
    http://jehiah.cz/a/printing-relative-dates-in-python
    http://stackoverflow.com/questions/11/how-do-i-calculate-relative-time
    """
    if not isinstance(d, datetime):
        d = datetime(d.year, d.month, d.day)
    if now and not isinstance(now, datetime):
        now = datetime(now.year, now.month, now.day)
    if not now:
        now = datetime.utcnow()
    delta = now - d
    minutes = delta.days * 24 * 60 + delta.seconds / 60
    
    if minutes < 0:
        return "not yet"
    if minutes < 1:
        return "just now"
    if minutes < 2:
        return "a minute ago"
    if minutes < 5:
        return "a few minutes ago"
    if minutes < 45:
        return "%d minutes ago" % int(minutes)
    if minutes < 90:
        return "an hour ago"
    
    hours = minutes / 60;
    if hours < 4:
        return "a few hours ago"
    if hours < 24:
        return "%d hours ago" % int(hours)
    
    midnight = datetime(now.year, now.month, now.day)
    hours_since_midnight = now - midnight
    days_since_midnight = delta - hours_since_midnight
    days = days_since_midnight.days + 1
    if days < 2:
        return "yesterday"
    if days < 7:
        return d.strftime("%A")
    if days < 31:
        return "%d days ago" % int(days)
    
    months = days / 30
    if months <= 1:
        return "one month ago"
    if months < 12:
        return "%d months ago" % months
    
    years = months / 12
    if years <= 1:
        return "one year ago"
    return "%d years ago" % years

def canonical_filename(title, film_series, season=-1, episode_char='e', episode=-1, episode_name='', ext="mkv", filename=""):
    if not title:
        title = decode_title_text(os.path.basename(filename)).title()
    name = []
    if season == -1:
        if film_series:
            name.append("%s-f%02d" % (film_series[0], int(film_series[1])))
        name.append(title)
    else:
        name.append(title)
        name.append("s%02d" % season)
    if episode > -1:
        name.append("%s%02d" % (episode_char, episode))
    if episode_name:
        name.append(episode_name)
    return encode_title_text("-".join(name) + ".%s" % ext)

def iter_dir(path, valid_extensions=None, exclude=None, verbose=False, recurse=False):
    if exclude is not None:
        try:
            exclude = re.compile(exclude)
        except:
            log.warning("Invalid regular expression %s" % exclude)
            pass
    videos = glob.glob(os.path.join(path, "*"))
    for video in videos:
        valid = False
        if os.path.isdir(video):
            if not video.endswith(".old"):
                if exclude:
                    match = cls.exclude.search(video)
                    if match:
                        log.debug("Skipping dir %s" % video)
                        continue
                log.debug("Checking dir %s" % video)
                if recurse:
                    iter_dir(video, valid_extensions, exclude, verbose, True)
        elif os.path.isfile(video):
            log.debug("Checking %s" % video)
            if valid_extensions:
                for ext in valid_extensions:
                    if video.endswith(ext):
                        valid = True
                        log.debug("Found valid media: %s" % video)
                        break
            else:
                valid = True
            if valid:
                yield video

def parse_int_string(nputstr=""):
    """Return list of integers from comma separated ranges
    
    Modified from http://thoughtsbyclayg.blogspot.com/2008/10/parsing-list-
    of-numbers-in-python.html to return ranges in order specified, rather than
    sorting the entire resulting list
    
    >>> parse_int_string("1,4,9-12")
    [1, 4, 9, 10, 11, 12]
    >>> parse_int_string("4,5,1,6")
    [4, 5, 1, 6]
    >>> parse_int_string("4,6-8,1,5,2")
    [4, 6, 7, 8, 1, 5, 2]
    """
    selection = []
    invalid = set()
    # tokens are comma seperated values
    tokens = [x.strip() for x in nputstr.split(',')]
    for i in tokens:
        try:
            # typically tokens are plain old integers
            selection.append(int(i))
        except:
            # if not, then it might be a range
            try:
               token = [int(k.strip()) for k in i.split('-')]
               if len(token) > 1:
                  token.sort()
                  # we have items seperated by a dash
                  # try to build a valid range
                  first = token[0]
                  last = token[len(token)-1]
                  for x in range(first, last+1):
                     selection.append(x)
            except:
               # not an int and not a range...
               invalid.add(i)
    # Report invalid tokens before returning valid selection
    if invalid:
        print "Invalid set: " + str(invalid)
    #ordered = list(selection)
    #ordered.sort()
    return selection

# lexical token symbols
DQUOTED, SQUOTED, UNQUOTED, COMMA, NEWLINE = xrange(5)

_pattern_tuples = (
    (r'"[^"]*"', DQUOTED),
    (r"'[^']*'", SQUOTED),
    (r",", COMMA),
    (r"$", NEWLINE), # matches end of string OR \n just before end of string
    (r"[^,\n]+", UNQUOTED), # order in the above list is important
    )
_matcher = re.compile(
    '(' + ')|('.join([i[0] for i in _pattern_tuples]) + ')',
    ).match
_toktype = [None] + [i[1] for i in _pattern_tuples]
# need dummy at start because re.MatchObject.lastindex counts from 1 

def csv_split(text):
    """Split a csv string into a list of fields.
    Fields may be quoted with " or ' or be unquoted.
    An unquoted string can contain both a " and a ', provided neither is at
    the start of the string.
    A trailing \n will be ignored if present.
    
    From http://stackoverflow.com/questions/4982531/how-do-i-split-a-comma-delimited-string-in-python-except-for-the-commas-that-are
    """
    fields = []
    pos = 0
    want_field = True
    while 1:
        m = _matcher(text, pos)
        if not m:
            raise ValueError("Problem at offset %d in %r" % (pos, text))
        ttype = _toktype[m.lastindex]
        if want_field:
            if ttype in (DQUOTED, SQUOTED):
                fields.append(m.group(0)[1:-1])
                want_field = False
            elif ttype == UNQUOTED:
                fields.append(m.group(0))
                want_field = False
            elif ttype == COMMA:
                fields.append("")
            else:
                assert ttype == NEWLINE
                fields.append("")
                break
        else:
            if ttype == COMMA:
                want_field = True
            elif ttype == NEWLINE:
                break
            else:
                print "*** Error dump ***", ttype, repr(m.group(0)), fields
                raise ValueError("Missing comma at offset %d in %r" % (pos, text))
        pos = m.end(0)
    return fields

class ExeRunner(object):
    exe_name = None
    default_args = []
    verbose = 0
    logfile = None
    loglevel = 2
    
    def __init__(self, source, options=None, test_stdout=None, test_stderr=None, *args, **kwargs):
        self.setCommandLine(source, options=options, *args, **kwargs)
        if test_stdout is not None or test_stderr is not None:
            self.testOutputProcessing(test_stdout, test_stderr)
    
    def verifyKeywordExists(self, key, kwargs):
        if key not in kwargs:
            kwargs[key] = []
    
    def prefixKeywordArgs(self, kwargs, key, *args):
        self.verifyKeywordExists(key, kwargs)
        current = list(*args)
        current.extend(kwargs[key])
        kwargs[key] = ",".join(current)

    def appendKeywordArgs(self, kwargs, key, *args):
        self.verifyKeywordExists(key, kwargs)
        current = kwargs[key]
        current.extend(*args)
        kwargs[key] = ",".join(current)

    def setCommandLine(self, source, *args, **kwargs):
        self.args = []
        if source is not None:
            self.args.append(source)
        if not args:
            args = self.default_args
        for arg in args:
            self.args.extend(arg.split())
        for key, value in kwargs.iteritems():
            self.args.append("-%s" % key)
            self.args.append(value)
    
    def get_command_line(self):
        args = [self.exe_name]
        args.extend(self.args)
        return args
    
    def popen(self):
        import subprocess
        
        args = self.get_command_line()
        self.vprint(1, "popen: %s" % str(args))
        try:
            p = subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        except OSError, e:
            raise RuntimeError("Error with executable %s: %s" % (self.exe_name, e))
        return p
    
    def run(self):
        p = self.popen()
        stdout, stderr = p.communicate()
        self.parseOutput(stdout)
        self.parseErrors(stderr)
    
    def testOutputProcessing(self, stdout, stderr):
        if stdout is None:
            stdout = ""
        if stderr is None:
            stderr = ""
        self.parseOutput(stdout)
        self.parseErrors(stderr)
    
    def parseOutput(self, output):
        self.vprint(2, output)
    
    def parseErrors(self, output):
        self.vprint(2, output)
        pass
    
    @classmethod
    def vprint(cls, verbosity_level, txt=""):
        if cls.verbose >= verbosity_level or cls.logfile is not None:
            if not isinstance(txt, basestring):
                txt = str(txt)
            if cls.verbose >= verbosity_level:
                print "%s" % txt.encode('utf-8')
            if cls.logfile is not None and cls.loglevel >= verbosity_level:
                cls.logfile.write("%s\n" % txt)

def vprint(verbosity_level, txt=""):
    ExeRunner.vprint(verbosity_level, txt)


if __name__ == "__main__":
    now = datetime(2012,4,3,12,34,56)
    print "Now: %s" % now.strftime("%A, %d %B %Y %I:%M%p")
    for d in [
        datetime(2012,4,3,1,23,45),
        datetime(2012,4,2,12,23,45),
        datetime(2012,4,2,1,23,45),
        datetime(2012,4,1,23,1,2),
        datetime(2012,4,1,1,23,45),
        datetime(2012,3,31,1,23,45),
        datetime(2012,3,30,1,23,45),
        datetime(2012,3,29,1,23,45),
        datetime(2012,3,28,1,23,45),
        datetime(2012,3,27,1,23,45),
        datetime(2012,3,12),
        datetime(2012,3,3),
        datetime(2012,2,12),
        datetime(2012,2,2),
        datetime(2012,1,12),
        datetime(2011,1,12),
        ]:
        print "%s: %s" % (d.strftime("%A, %d %B %Y %I:%M%p"), time_since(d, now))
