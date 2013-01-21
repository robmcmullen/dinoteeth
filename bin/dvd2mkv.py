#!/usr/bin/env python
"""Rip DVDs and encode to mkv

Tested on linux; probably will work under all unix-like OSes.  Not tested (and
probably will not work) on Windows.

Requires the following programs to be available on your PATH:

mkvmerge, mkvextract, mkvpropedit from mkvtoolnix
HandBrakeCLI
mplayer (only if audio gain normalization is used)
normalize (only if audio gain normalization is used)
"""

import os, sys, re, tempfile, time, copy
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..")) # to find third_party
try:
    import argparse
except:
    import dinoteeth.third_party.argparse as argparse
from dinoteeth.utils import encode_title_text, canonical_filename, parse_int_string, csv_split, ExeRunner, vprint, find_next_episode_number
from dinoteeth.transcoder import *

import dinoteeth.settings as settings
from dinoteeth.third_party.configobj import ConfigObj
from dinoteeth.third_party.validate import Validator

class TrackInfo(object):
    def __init__(self):
        self.order = list()
        self.name = dict()
    
    def __str__(self):
        return str(self.name)
    
    def add_track(self, index, name):
        self.order.append(index)
        self.name[index] = name
    
    def iter_tracks(self):
        for i in self.order:
            yield i, self.name[i]

def parse_episode_info(starting, dvd_titles, spec):
    # set defaults
    numbers = range(starting, starting + len(dvd_titles))
    names = [""] * len(dvd_titles)
    
    def parse_episode_numbers(number_spec):
        tokens = csv_split(number_spec)
        tokens = [int(t) for t in tokens]
        # Throw away any extra specified items in the list beyond the number of
        # expected dvd titles
        if len(tokens) > len(dvd_titles):
            tokens = tokens[0:len(dvd_titles)]
        elif len(tokens) > 0:
            num = tokens[-1] + 1
            for i in range(len(tokens), len(dvd_titles)):
                numbers[i] = num
                num += 1
        else:
            return
        numbers[0:len(tokens)] = tokens
    
    def parse_episode_names(number_spec):
        tokens = csv_split(number_spec)
        if len(tokens) > len(dvd_titles):
            tokens = tokens[0:len(dvd_titles)]
        names[0:len(tokens)] = tokens

    if len(spec) == 0:
        pass
    elif len(spec) == 1:
        try:
            parse_episode_numbers(spec[0])
        except ValueError:
            parse_episode_names(spec[0])
    elif len(spec) == 2:
        parse_episode_numbers(spec[0])
        parse_episode_names(spec[1])
    else:
        raise RuntimeError("Incorrect format specification")
    return numbers, names

def parse_stream_names(spec):
    info = TrackInfo()
    if spec:
        tracks = parse_int_string(spec[0])
        names = [''] * len(tracks)
        if len(spec) > 1:
            tokens = csv_split(spec[1])
            names[0:len(tokens)] = tokens
        for t, n in zip(tracks, names):
            info.add_track(t, n)
    return info

class OrderedNamespace(argparse.Namespace):
    def __init__(self, **kwargs):
        self.__arg_call_order__ = []
        argparse.Namespace.__init__(self, **kwargs)

    def __setattr__(self, name, value):
        if self.__dict__.has_key(name):
            self.__arg_call_order__.append(name)
        self.__dict__[name] = value
    
    def _prepend(self, other):
        a = other
        b = self
        self._merge(other, a, b)
        
    def _append(self, other):
        a = self
        b = other
        self._merge(other, a, b)
    
    def _merge(self, other, a, b):
        order = a.__arg_call_order__[:]
        order.extend(b.__arg_call_order__[:])
        d1 = {}
        d1.update(self.__dict__)
        for k in other.__arg_call_order__: # only override non-default values in other
            d1[k] = other.__dict__[k]
        for k,v in other.__dict__.iteritems(): # add any missing default items from b
            if k not in d1:
                d1[k] = v
        self.__dict__.clear()
        for k,v in d1.iteritems():
            self.__dict__[k] = v
        self.__arg_call_order__ = order
    
    def _latest_of(self, k1, k2):
        try:
            if self.__arg_call_order__.index(k1) > self.__arg_call_order__.index(k2):
                return k1
        except ValueError:
            if k1 in self.__arg_call_order__:
                return k1
        return k2

    def _get_kwargs(self):
        '''For obfuscating the __arg_call_order__ variable. Not really needed'''
        return [x for x in self.__dict__.items() if x[0] !='__arg_call_order__']

if __name__ == "__main__":
    global_parser = argparse.ArgumentParser(description="Convert titles in a DVD image to Matroska files")
    global_parser.add_argument("-v", "--verbose", default=0, action="count")
    global_parser.add_argument("--dry-run", action="store_true", default=False, help="Don't encode, just show what would have been encoded")
    global_parser.add_argument("--min-time", action="store", type=int, default=2,
                      help="Minimum time (minutes) for bonus feature to be valid")
    global_parser.add_argument("--scanfile", action="store_true", default=True, help="Store output of scan to increase speed on subsequent runs (default handbrake.scan)")
    global_parser.add_argument("--no-scanfile", action="store_true", dest="scanfile", default=True, help="No not store output of scan to increase speed on subsequent runs (default handbrake.scan)")
    global_parser.add_argument("--log", action="store_true", default=True, help="Store output of scan to increase speed on subsequent runs (default handbrake.log)")
    global_parser.add_argument("--tmp", action="store", default="", help="Directory for temporary files created during encoding process")
    global_parser.add_argument("--overwrite", action="store_true", default=False, help="Overwrite existing encoded files")
    global_parser.add_argument("-o", action="store", dest="output", default="", help="Output directory  (default current directory)")
    global_parser.add_argument("--info", action="store_true", dest="info", default=False, help="Only print info")
    global_parser.add_argument("-f", action="store", dest="film_series", default=[], nargs=2, metavar=("SERIES_NAME", "FILM_NUMBER"), help="Film series name and number in series (e.g. \"James Bond\" 1 or \"Harry Potter\" 8 etc.)")
    global_parser.add_argument("-s", action="store", type=int, dest="season", default=-1, help="Season number")
    global_parser.add_argument("--lang", action="store", default="eng",
                      help="Preferred language")
    global_parser.add_argument("-i", action="store", dest="input", help="Path to DVD image")

    # Testing options not used for normal encoding tasks
    global_parser.add_argument("--mkv", action="store", help="Display audio information of specified .mkv file")
    global_parser.add_argument("--mkv-names", action="store", metavar=("MKV_FILE", "DVD_TITLE"), nargs=2, help="Rename tracks in .mkv file")


    sticky_parser = argparse.ArgumentParser(description="Sticky arguments that remain set until explicitly reset")
    sticky_parser.add_argument("-n", action="store", dest="name", default='', help="Movie or TV Series name")
    sticky_parser.add_argument("--ext", action="store", dest="ext", default="mkv", help="Output file format (default %(default)s)")
    sticky_parser.add_argument("--cc-first", action="store_true", dest="cc_first", default=True, help="Place closed captions before vobsub (DVD image subtitles)")
    sticky_parser.add_argument("--vobsub-first", action="store_false", dest="cc_first", default=True, help="Place vobsub (DVD image subtitles) before closed captions")
    
    # Video options
    sticky_parser.add_argument("-b", "--vb", action="store", dest="video_bitrate", type=int, default=0, help="Video bitrate (kb/s)")
    sticky_parser.add_argument("-g", "--grayscale", action="store_true", dest="grayscale", default=False, help="Grayscale encoding")
    sticky_parser.add_argument("--color", action="store_false", dest="grayscale", default=False, help="Color encoding (default)")
    sticky_parser.add_argument("--crop", action="store", dest="crop", default="0:0:0:0", help="Crop parameters (default %(default)s)")
    sticky_parser.add_argument("--autocrop", action="store_true", default=False, help="Use autocrop as determined from the scan (default %(default)s)")
    sticky_parser.add_argument("--decomb", action="store_true", default=False, help="Add deinterlace (decomb) filter (slows processing by up to 50%)")
    sticky_parser.add_argument("--video-encoder", action="store", default="x264", help="Video encoder (default %(default)s)")
    sticky_parser.add_argument("--x264-preset", action="store", default="", help="x264 encoder preset")
    sticky_parser.add_argument("--x264-tune", action="store", default="film", help="x264 encoder tuning (typically either 'film' or 'animation')")
    sticky_parser.add_argument("--qHD", "--540", "--960", action="store_const", dest="hd_width", default=0, const=960, help="Encode at 960x540 (qHD)")
    sticky_parser.add_argument("--720p", "--720", "--1280", action="store_const", dest="hd_width", default=0, const=1280, help="Encode at 1280x720 (720p HD)")
    sticky_parser.add_argument("--768p", "--768", "--1360", "--1366", action="store_const", dest="hd_width", default=0, const=1360, help="Encode at 1360x768 (768p HD)")
    sticky_parser.add_argument("--1080p", "--1080", "--1920", action="store_const", dest="hd_width", default=0, const=1920, help="Encode at 1920x1080 (Full HD)")
    
    # Audio options
    sticky_parser.add_argument("--audio-encoder", action="store", default="faac", help="Audio encoder (default %(default)s)")
    sticky_parser.add_argument("-B", "--ab", action="store", dest="audio_bitrate", type=int, default=160, help="Audio bitrate (kb/s)")
    sticky_parser.add_argument("--normalize", action="store_true", default=True, help="Automatically select gain values to normalize audio (uses an extra encoding pass)")
    sticky_parser.add_argument("--no-normalize", dest="normalize", action="store_false", default=True, help="Automatically select gain values to normalize audio (uses an extra encoding pass)")
    sticky_parser.add_argument("--gain", action="store", default="", help="Specify audio gain (dB, positive values amplify). Comma separated list, otherwise gain value used for all tracks")

    # Testing options not used for normal encoding tasks
    sticky_parser.add_argument("--fast", action="store_true", default=False, help="Fast encoding mode to small video at constant 5fps")
    sticky_parser.add_argument("--preview", action="store", type=int, default=0, help="Preview the first PREVIEW chapters")


    title_parser = argparse.ArgumentParser(description="DVD Title options")
    title_parser.add_argument("-t", action="store", dest="dvd_title", default="", help="DVD title number (or list or range) to process")
    title_parser.add_argument("-e", action="store", dest="episode", default=None, nargs="*", metavar=("NUMBER", "NAME,NAME"), help="Optional starting episode number and optional comma separated list of episode names")
    title_parser.add_argument("-x", action="store", dest="bonus", default=None, nargs="*", metavar=("NUMBER", "NAME,NAME"), help="Optional starting bonus feature number and optional comma separated list of bonus feature names")
    title_parser.add_argument("-a", action="store", dest="audio", default=None, nargs="+", metavar="AUDIO_TRACK_NUMBER(s) [TITLE,TITLE...]", help="Range of audio track numbers and optional audio track names.  Note: if multiple DVD titles are specified in this title block, the audio tracks will apply to ALL of them")
    title_parser.add_argument("-c", action="store", dest="subtitles", default=None, nargs="+", metavar="SUBTITLE_TRACK_NUMBER(s) [TITLE,TITLE...]", help="Range of subtitle caption numbers and optional corresponding subtitle track names.  Note: if multiple DVD titles are specified in this title block, the audio tracks will apply to ALL of them")
    
    default_parser = argparse.ArgumentParser(description="Default Parser")
    default_parser.add_argument("-c", "--conf_file", default="",
                help="Specify config file to replace global config file loaded from user's home directory", metavar="FILE")
    options, extra_args = default_parser.parse_known_args()
    defaults = {}
    if options.conf_file:
        conf_file = options.conf_file
    else:
        conf_file = os.path.expanduser("~/.dinoteeth/settings.ini")
    configspec = ConfigObj(settings.default_conf.splitlines(), list_values=False)
    ini = ConfigObj(conf_file, configspec=configspec)
    ini.validate(Validator())
    
    # parameters in other sections are only specified through config file
    for section in ["metadata", "transcode", ]:
        user = dict(ini[section])
        print "user [%s]: %s" % (section, user)
        known = dict(configspec[section])
        print "known [%s]: %s" % (section, known)
        for k in known.keys():
            setattr(settings, k, user[k])

    media_paths = []
    for path, flags in ini["media_paths"].iteritems():
        if settings.media_root and not os.path.isabs(path):
            path = os.path.join(settings.media_root, path)
        if os.path.isdir(path):
            media_paths.append(path)
            print path
    
    # Split argument list by the "-t" option so that each "-t" can have its
    # own arguments
    arg_sets = []
    start = 1
    while start < len(sys.argv):
        try:
            end = sys.argv.index("-t", start + 1)
            arg_set = sys.argv[start:end]
            arg_sets.append(arg_set)
            start = end
        except ValueError:
            arg_sets.append(sys.argv[start:])
            break
    global_args = arg_sets[0]
    title_args = arg_sets[1:]
    
    global_options, sticky_args = global_parser.parse_known_args(global_args, namespace=OrderedNamespace())
    ExeRunner.verbose = global_options.verbose
    sticky_options, extra_args = sticky_parser.parse_known_args(sticky_args, namespace=OrderedNamespace())
    sticky_options._prepend(global_options)
    title_options = []
    for args in title_args:
        new_sticky_options, extra_args = sticky_parser.parse_known_args(args, namespace=OrderedNamespace())
        sticky_options._append(new_sticky_options)
        options, extra_args = title_parser.parse_known_args(extra_args, namespace=OrderedNamespace())
        options._prepend(sticky_options)
        vprint(1, "title(s): %s" % options.dvd_title)
        if extra_args:
            new_global_options, ignored_args = global_parser.parse_known_args(extra_args, namespace=OrderedNamespace())
            global_options._append(new_global_options)
            ExeRunner.verbose = global_options.verbose
        vprint(1, "global: %s" % global_options)
        vprint(1, "sticky: %s" % sticky_options)
        vprint(1, "options: %s" % options)
        title_options.append(options)
    
    queue = []
    vprint(1, "final global options: %s" % global_options)
    source = global_options.input
    if not source:
        global_parser.print_usage()
        global_parser.exit()
    
    if global_options.log:
        logfile = HandBrakeScanner.get_scanfile(source).replace(".scan", ".log")
        ExeRunner.logfile = open(logfile, "w")
    
    if global_options.tmp:
        os.environ["TEMP"] = global_options.tmp
    
    scan = HandBrakeScanner(source, options=global_options)
    scan.run()
    
    if global_options.mkv:
        mkv = MkvScanner(global_options.mkv)
        mkv.run()
        print scan.handbrake_to_mkv
        extractor = MkvAudioExtractor(global_options.mkv, mkv=mkv)
        extractor.run()
        normalizer = AudioGain(global_options.mkv, extractor=extractor)
        normalizer.run()
        sys.exit()
    if global_options.mkv_names:
        print scan
        filename = global_options.mkv_names[0]
        dvd_title = int(global_options.mkv_names[1])
        mkv = MkvScanner(filename)
        mkv.run()
        print mkv
        encoder = HandBrakeEncoder(source, scan, filename, dvd_title, global_options)
        prop = MkvPropEdit(filename, options=options, dvd_title=dvd_title, scan=scan, mkv=mkv, encoder=encoder)
        prop.run()
        sys.exit()

    if len(title_options) > 0:
        episode_number = 1
        bonus_number = 1
        seen_film_series = False
        for options in title_options:
            dvd_title_spec = options.dvd_title
            if not dvd_title_spec:
                title_parser.error("DVD title number must be specified.") 
            dvd_titles = parse_int_string(dvd_title_spec)
            
            audio = parse_stream_names(options.audio)
            subtitles = parse_stream_names(options.subtitles)
            
            if options.episode is not None:
                if len(options.episode) == 0:
                    next = find_next_episode_number(options.name, options.season, "e", source, media_paths)
                    numbers = range(next, next + len(dvd_titles))
                    names = [""] * len(dvd_titles)
                else:
                    numbers, names = parse_episode_info(episode_number, dvd_titles, options.episode)
                
                # add each episode to queue
                for dvd_title, episode, name in zip(dvd_titles, numbers, names):
                    filename = canonical_filename(options.name, options.film_series, options.season, "e", episode, name, options.ext, filename=source)
                    try:
                        encoder = HandBrakeEncoder(source, scan, filename, dvd_title, audio, subtitles, options)
                        queue.append(encoder)
                    except HandBrakeScanError:
                        print "Bad title number %s!  Skipping." % dvd_title
                
                # set up next default episode number
                episode_number = numbers[-1] + 1
            
            elif options.bonus is not None:
                if len(options.bonus) == 0:
                    next = find_next_episode_number(options.name, options.season, "x", source, media_paths)
                    numbers = range(next, next + len(dvd_titles))
                    names = [""] * len(dvd_titles)
                else:
                    numbers, names = parse_episode_info(bonus_number, dvd_titles, options.bonus)
                
                # add each bonus feature to queue
                for dvd_title, episode, name in zip(dvd_titles, numbers, names):
                    filename = canonical_filename(options.name, options.film_series, options.season, "x", episode, name, options.ext, filename=source)
                    try:
                        encoder = HandBrakeEncoder(source, scan, filename, dvd_title, audio, subtitles, options)
                        queue.append(encoder)
                    except HandBrakeScanError:
                        print "Bad title number %s!  Skipping." % dvd_title
                
                # set up next default episode number
                bonus_number = numbers[-1] + 1
            
            else:
                if seen_film_series:
                    options.film_series[1] = int(options.film_series[1]) + 1
                dvd_title = dvd_titles[0]
                filename = canonical_filename(options.name, options.film_series, options.season, None, None, None, options.ext, filename=source)
                try:
                    encoder = HandBrakeEncoder(source, scan, filename, dvd_title, audio, subtitles, options)
                    queue.append(encoder)
                except HandBrakeScanError:
                    print "Bad title number %s!  Skipping." % dvd_title
                seen_film_series = True

        for enc in queue:
            if global_options.dry_run:
                vprint(0, " ".join(enc.get_command_line()))
            else:
                try:
                    enc.run()
                except RuntimeError, e:
                    vprint(0, e)
                    break
    else:
        print scan
        
    if global_options.log:
        ExeRunner.logfile.close()
