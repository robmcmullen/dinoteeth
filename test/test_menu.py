#!/usr/bin/env python
# -*- coding: utf-8 -*-

from dinoteeth_test import *

from media import guess_custom
from config import Config
from database import DictDatabase
from model import MenuItem

class TestMenuMovies1(TestCase):
    def setUp(self):
        self.config = Config([])
        self.db = DictDatabase()
        self.config.parse_dir(self.db, "movies1")
        
    def testMenu1(self):
        results = self.db.find("movie")
        assert len(results) == 38
        h = results.hierarchy()
        h.pprint()
        self.assertEqual(len(h.children), 15)
        menu = self.root
        menu.add_hierarchy(h)
        self.assertEqual(len(menu.children), 15)
        self.assertEqual(menu.children[9].title, "The Hunt for Red October")
        self.assertEqual(menu.children[9].children[0].title, "The Hunt for Red October")
        self.assertEqual(menu.children[9].children[1].title, "  Play")


if __name__ == '__main__':
    test_all()
