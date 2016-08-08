#!/usr/bin/env python

import os
import sys
import argparse

# Create lists of edit points using: mpv --osd-level=2 --osd-fractions /nas/media/movies-hd/Apollo_13.mkv
#    frame advance: .
#    frame previous: ,

# Create each chunk using: /data/src/handbrake-current/build/HandBrakeCLI -i /nas/media/movies-hd/Apollo_13.mkv --start-at duration:0 --stop-at duration:41.875 -E copy:aac -o /tmp/apollo13a.mkv
#    stop at parameter is really the delta time from the start-at

# Merge chunks together using: mkvmerge -o /tmp/apollo13.mkv /tmp/apollo13a.mkv +/tmp/apollo13b.mkv   

class EditPoints(object):
    def __init__(self, source):
        self.source = source
        self.edit_points = []

    def __str__(self):
        lines = [self.source]
        for pt in self.edit_points:
            lines.append("  %s -> %s" % pt)
        return "\n".join(lines)

    def add_edit_point(self, start, end):
        self.edit_points.append((start, end))

def process(filename, options):
    edit = None
    with open(filename, "r") as fh:
        for line in fh:
            line = line.strip()
            if options.verbose: print line
            if line.startswith("#"):
                continue
            if not line:
                continue
            if edit is None:
                edit = EditPoints(line)
            else:
                times = line.split()
                edit.add_edit_point(*times)

    print edit



if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Convert MKV file based on edit points listed in the command file")
    parser.add_argument("-v", "--verbose", default=0, action="count")
    parser.add_argument("--dry-run", action="store_true", default=False, help="Don't encode, just show what would have been encoded")

    options, extra_args = parser.parse_known_args()
    for filename in extra_args:
        process(filename, options)