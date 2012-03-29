#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os, sys

from unittest import *

def currentPath():
    '''Returns the path in which the calling file is located.'''
    return os.path.dirname(os.path.join(os.getcwd(), sys._getframe(1).f_globals['__file__']))

def addImportPath(path):
    '''Function that adds the specified path to the import path. The path can be
    absolute or relative to the calling file.'''
    importPath = os.path.abspath(os.path.join(currentPath(), path))
    sys.path = [ importPath ] + sys.path

addImportPath('.')  # for the tests
addImportPath('..') # for import guessit

def getAllSubclassesOf(parent=object, subclassof=None):
    """
    Recursive call to get all classes that have a specified class
    in their ancestry.  The call to __subclasses__ only finds the
    direct, child subclasses of an object, so to find
    grandchildren and objects further down the tree, we have to go
    recursively down each subclasses hierarchy to see if the
    subclasses are of the type we want.

    @param parent: class used to find subclasses
    @type parent: class
    @param subclassof: class used to verify type during recursive calls
    @type subclassof: class
    @returns: list of classes
    """
    if subclassof is None:
        subclassof=parent
    subclasses={}

    # this call only returns immediate (child) subclasses, not
    # grandchild subclasses where there is an intermediate class
    # between the two.
    classes=parent.__subclasses__()
    for kls in classes:
        # FIXME: this seems to return multiple copies of the same class,
        # but I probably just don't understand enough about how python
        # creates subclasses
        # dprint("%s id=%s" % (kls, id(kls)))
        if issubclass(kls,subclassof):
            subclasses[kls] = 1
        # for each subclass, recurse through its subclasses to
        # make sure we're not missing any descendants.
        subs=getAllSubclassesOf(parent=kls)
        if len(subs)>0:
            for kls in subs:
                subclasses[kls] = 1
    return subclasses.keys()

def test_all():
    for case in getAllSubclassesOf(TestCase):
        if case.__module__ == "__main__":
            suite = TestLoader().loadTestsFromTestCase(case)
            TextTestRunner(verbosity=2).run(suite)

__all__ = ['test_all', 'TestCase']
