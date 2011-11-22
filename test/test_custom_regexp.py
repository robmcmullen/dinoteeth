#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# GuessIt - A library for guessing information from filenames
# Copyright (c) 2011 Nicolas Wack <wackou@gmail.com>
#
# GuessIt is free software; you can redistribute it and/or modify it under
# the terms of the Lesser GNU General Public License as published by
# the Free Software Foundation; either version 3 of the License, or
# (at your option) any later version.
#
# GuessIt is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# Lesser GNU General Public License for more details.
#
# You should have received a copy of the Lesser GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#


from guessittest import *
from media import guess_custom
from config import Config

class TestEpisode(TestGuessit):

    def testNewMatcher(self):
        config = Config([])
        regexps = config.get_custom_video_regexps()
        new_guesser = lambda filename: guess_custom(filename, regexps)
        self.checkMinimumFieldsCorrect(new_guesser, 'test_custom_regexp.yaml')


suite = allTests(TestEpisode)

if __name__ == '__main__':
    TextTestRunner(verbosity=2).run(suite)
