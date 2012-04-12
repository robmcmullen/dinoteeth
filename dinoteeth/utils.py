import os, sys, glob, logging, re
from datetime import datetime, timedelta

log = logging.getLogger("dinoteeth.utils")

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

def canonical_filename(title, film_series, season=-1, episode_char='e', episode=-1, episode_name='', ext="mkv"):
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
