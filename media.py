import os, sys, glob, re
import pyglet

import utils

from guessit import guess_file_info, Guess


def normalize_guess(guess):
    if guess['type'] == 'movie' and 'title' not in guess:
        title, _ = os.path.splitext(os.path.basename(filename))
        guess['title'] = unicode(title)

def guess_media_info(pathname):
    filename = utils.decode_title_text(pathname)
    guess = guess_file_info(filename, "autodetect", info=['filename'])
    return guess

def guess_custom(pathname, regexps):
    filename, _ = os.path.splitext(pathname)
    for regexp in regexps:
        r = re.compile(regexp)
        match = r.match(filename)
        if match:
            metadata = match.groupdict()
            for prop, value in metadata.items():
                if prop in ('season', 'episodeNumber', 'year', 'extraNumber'):
                    if metadata[prop] is not None:
                        metadata[prop] = int(metadata[prop])
                if prop in ('title', 'extraTitle', 'series', 'filmSeries'):
                    if metadata[prop]:
                        metadata[prop] = utils.decode_title_text(metadata[prop])
                    else:
                        del metadata[prop]
            if 'season' in metadata:
                metadata['type'] = 'episode'
            else:
                metadata['type'] = 'movie'
            if 'filmSeries' in metadata:
                if 'title' not in metadata:
                    if 'episodeNumber' in metadata and metadata['episodeNumber'] > 1:
                        metadata['title'] = "%s %d" % (metadata['filmSeries'], metadata['episodeNumber'])
                    else:
                        metadata['title'] = metadata['filmSeries']
            guess = Guess(metadata, confidence = 1.0)
            return guess
    return None

