#!/usr/bin/env python
# -*- coding: utf-8 -*-

from dinoteeth_test import *

from media import guess_custom
from config import Config, RootMenu
from database import DictDatabase
from model import MenuItem

class TestMenuMovies1(TestCase):
    def setUp(self):
        self.config = Config([])
        self.db = DictDatabase()
        self.root = RootMenu(self.db)
        self.config.parse_dir(self.root, "movies1")
        
    def testMenu1(self):
        results = self.db.find("movie")
        assert len(results) == 38
        h = results.hierarchy()
        self.assertEqual(len(h.children), 15)
        menu = MenuItem("Movies")
        menu.add_hierarchy(h)
        menu.pprint()
        self.assertEqual(len(menu.children), 15)
        self.assertEqual(menu.children[9].title, "The Hunt for Red October")
        self.assertEqual(menu.children[9].children[0].title, "The Hunt for Red October")
        self.assertEqual(menu.children[9].children[1].title, "  Play")


if __name__ == '__main__':
    test_all()
