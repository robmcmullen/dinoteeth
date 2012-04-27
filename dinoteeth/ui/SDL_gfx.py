'''Wrapper for SDL_gfxPrimitives.h

Generated with:
/usr/bin/ctypesgen.py -L/usr/lib -I/usr/include/SDL -lSDL_gfx /usr/include/SDL/SDL_gfxPrimitives.h -o SDL_gfx.py

Do not modify this file.
'''

__docformat__ =  'restructuredtext'

# Begin preamble

import ctypes, os, sys
from ctypes import *

_int_types = (c_int16, c_int32)
if hasattr(ctypes, 'c_int64'):
    # Some builds of ctypes apparently do not have c_int64
    # defined; it's a pretty good bet that these builds do not
    # have 64-bit pointers.
    _int_types += (c_int64,)
for t in _int_types:
    if sizeof(t) == sizeof(c_size_t):
        c_ptrdiff_t = t
del t
del _int_types

class c_void(Structure):
    # c_void_p is a buggy return type, converting to int, so
    # POINTER(None) == c_void_p is actually written as
    # POINTER(c_void), so it can be treated as a real pointer.
    _fields_ = [('dummy', c_int)]

def POINTER(obj):
    p = ctypes.POINTER(obj)

    # Convert None to a real NULL pointer to work around bugs
    # in how ctypes handles None on 64-bit platforms
    if not isinstance(p.from_param, classmethod):
        def from_param(cls, x):
            if x is None:
                return cls()
            else:
                return x
        p.from_param = classmethod(from_param)

    return p

class UserString:
    def __init__(self, seq):
        if isinstance(seq, basestring):
            self.data = seq
        elif isinstance(seq, UserString):
            self.data = seq.data[:]
        else:
            self.data = str(seq)
    def __str__(self): return str(self.data)
    def __repr__(self): return repr(self.data)
    def __int__(self): return int(self.data)
    def __long__(self): return long(self.data)
    def __float__(self): return float(self.data)
    def __complex__(self): return complex(self.data)
    def __hash__(self): return hash(self.data)

    def __cmp__(self, string):
        if isinstance(string, UserString):
            return cmp(self.data, string.data)
        else:
            return cmp(self.data, string)
    def __contains__(self, char):
        return char in self.data

    def __len__(self): return len(self.data)
    def __getitem__(self, index): return self.__class__(self.data[index])
    def __getslice__(self, start, end):
        start = max(start, 0); end = max(end, 0)
        return self.__class__(self.data[start:end])

    def __add__(self, other):
        if isinstance(other, UserString):
            return self.__class__(self.data + other.data)
        elif isinstance(other, basestring):
            return self.__class__(self.data + other)
        else:
            return self.__class__(self.data + str(other))
    def __radd__(self, other):
        if isinstance(other, basestring):
            return self.__class__(other + self.data)
        else:
            return self.__class__(str(other) + self.data)
    def __mul__(self, n):
        return self.__class__(self.data*n)
    __rmul__ = __mul__
    def __mod__(self, args):
        return self.__class__(self.data % args)

    # the following methods are defined in alphabetical order:
    def capitalize(self): return self.__class__(self.data.capitalize())
    def center(self, width, *args):
        return self.__class__(self.data.center(width, *args))
    def count(self, sub, start=0, end=sys.maxint):
        return self.data.count(sub, start, end)
    def decode(self, encoding=None, errors=None): # XXX improve this?
        if encoding:
            if errors:
                return self.__class__(self.data.decode(encoding, errors))
            else:
                return self.__class__(self.data.decode(encoding))
        else:
            return self.__class__(self.data.decode())
    def encode(self, encoding=None, errors=None): # XXX improve this?
        if encoding:
            if errors:
                return self.__class__(self.data.encode(encoding, errors))
            else:
                return self.__class__(self.data.encode(encoding))
        else:
            return self.__class__(self.data.encode())
    def endswith(self, suffix, start=0, end=sys.maxint):
        return self.data.endswith(suffix, start, end)
    def expandtabs(self, tabsize=8):
        return self.__class__(self.data.expandtabs(tabsize))
    def find(self, sub, start=0, end=sys.maxint):
        return self.data.find(sub, start, end)
    def index(self, sub, start=0, end=sys.maxint):
        return self.data.index(sub, start, end)
    def isalpha(self): return self.data.isalpha()
    def isalnum(self): return self.data.isalnum()
    def isdecimal(self): return self.data.isdecimal()
    def isdigit(self): return self.data.isdigit()
    def islower(self): return self.data.islower()
    def isnumeric(self): return self.data.isnumeric()
    def isspace(self): return self.data.isspace()
    def istitle(self): return self.data.istitle()
    def isupper(self): return self.data.isupper()
    def join(self, seq): return self.data.join(seq)
    def ljust(self, width, *args):
        return self.__class__(self.data.ljust(width, *args))
    def lower(self): return self.__class__(self.data.lower())
    def lstrip(self, chars=None): return self.__class__(self.data.lstrip(chars))
    def partition(self, sep):
        return self.data.partition(sep)
    def replace(self, old, new, maxsplit=-1):
        return self.__class__(self.data.replace(old, new, maxsplit))
    def rfind(self, sub, start=0, end=sys.maxint):
        return self.data.rfind(sub, start, end)
    def rindex(self, sub, start=0, end=sys.maxint):
        return self.data.rindex(sub, start, end)
    def rjust(self, width, *args):
        return self.__class__(self.data.rjust(width, *args))
    def rpartition(self, sep):
        return self.data.rpartition(sep)
    def rstrip(self, chars=None): return self.__class__(self.data.rstrip(chars))
    def split(self, sep=None, maxsplit=-1):
        return self.data.split(sep, maxsplit)
    def rsplit(self, sep=None, maxsplit=-1):
        return self.data.rsplit(sep, maxsplit)
    def splitlines(self, keepends=0): return self.data.splitlines(keepends)
    def startswith(self, prefix, start=0, end=sys.maxint):
        return self.data.startswith(prefix, start, end)
    def strip(self, chars=None): return self.__class__(self.data.strip(chars))
    def swapcase(self): return self.__class__(self.data.swapcase())
    def title(self): return self.__class__(self.data.title())
    def translate(self, *args):
        return self.__class__(self.data.translate(*args))
    def upper(self): return self.__class__(self.data.upper())
    def zfill(self, width): return self.__class__(self.data.zfill(width))

class MutableString(UserString):
    """mutable string objects

    Python strings are immutable objects.  This has the advantage, that
    strings may be used as dictionary keys.  If this property isn't needed
    and you insist on changing string values in place instead, you may cheat
    and use MutableString.

    But the purpose of this class is an educational one: to prevent
    people from inventing their own mutable string class derived
    from UserString and than forget thereby to remove (override) the
    __hash__ method inherited from UserString.  This would lead to
    errors that would be very hard to track down.

    A faster and better solution is to rewrite your program using lists."""
    def __init__(self, string=""):
        self.data = string
    def __hash__(self):
        raise TypeError, "unhashable type (it is mutable)"
    def __setitem__(self, index, sub):
        if index < 0:
            index += len(self.data)
        if index < 0 or index >= len(self.data): raise IndexError
        self.data = self.data[:index] + sub + self.data[index+1:]
    def __delitem__(self, index):
        if index < 0:
            index += len(self.data)
        if index < 0 or index >= len(self.data): raise IndexError
        self.data = self.data[:index] + self.data[index+1:]
    def __setslice__(self, start, end, sub):
        start = max(start, 0); end = max(end, 0)
        if isinstance(sub, UserString):
            self.data = self.data[:start]+sub.data+self.data[end:]
        elif isinstance(sub, basestring):
            self.data = self.data[:start]+sub+self.data[end:]
        else:
            self.data =  self.data[:start]+str(sub)+self.data[end:]
    def __delslice__(self, start, end):
        start = max(start, 0); end = max(end, 0)
        self.data = self.data[:start] + self.data[end:]
    def immutable(self):
        return UserString(self.data)
    def __iadd__(self, other):
        if isinstance(other, UserString):
            self.data += other.data
        elif isinstance(other, basestring):
            self.data += other
        else:
            self.data += str(other)
        return self
    def __imul__(self, n):
        self.data *= n
        return self

class String(MutableString, Union):

    _fields_ = [('raw', POINTER(c_char)),
                ('data', c_char_p)]

    def __init__(self, obj=""):
        if isinstance(obj, (str, unicode, UserString)):
            self.data = str(obj)
        else:
            self.raw = obj

    def __len__(self):
        return self.data and len(self.data) or 0
    
    def from_param(cls, obj):
        # Convert None or 0
        if obj is None or obj == 0:
            return cls(POINTER(c_char)())

        # Convert from String
        elif isinstance(obj, String):
            return obj

        # Convert from str
        elif isinstance(obj, str):
            return cls(obj)
        
        # Convert from c_char_p
        elif isinstance(obj, c_char_p):
            return obj
        
        # Convert from POINTER(c_char)
        elif isinstance(obj, POINTER(c_char)):
            return obj
        
        # Convert from raw pointer
        elif isinstance(obj, int):
            return cls(cast(obj, POINTER(c_char)))

        # Convert from object
        else:
            return String.from_param(obj._as_parameter_)
    from_param = classmethod(from_param)

def ReturnString(obj):
    return String.from_param(obj)

# As of ctypes 1.0, ctypes does not support custom error-checking
# functions on callbacks, nor does it support custom datatypes on
# callbacks, so we must ensure that all callbacks return
# primitive datatypes.
#
# Non-primitive return values wrapped with UNCHECKED won't be
# typechecked, and will be converted to c_void_p.
def UNCHECKED(type):
    if (hasattr(type, "_type_") and isinstance(type._type_, str)
        and type._type_ != "P"):
        return type
    else:
        return c_void_p

# ctypes doesn't have direct support for variadic functions, so we have to write
# our own wrapper class
class _variadic_function(object):
    def __init__(self,func,restype,argtypes):
        self.func=func
        self.func.restype=restype
        self.argtypes=argtypes
    def _as_parameter_(self):
        # So we can pass this variadic function as a function pointer
        return self.func
    def __call__(self,*args):
        fixed_args=[]
        i=0
        for argtype in self.argtypes:
            # Typecheck what we can
            fixed_args.append(argtype.from_param(args[i]))
            i+=1
        return self.func(*fixed_args+list(args[i:]))


# End preamble

_libs = {}
_libdirs = ['/usr/lib']

# Begin loader

# ----------------------------------------------------------------------------
# Copyright (c) 2008 David James
# Copyright (c) 2006-2008 Alex Holkner
# All rights reserved.
# 
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions 
# are met:
#
#  * Redistributions of source code must retain the above copyright
#    notice, this list of conditions and the following disclaimer.
#  * Redistributions in binary form must reproduce the above copyright 
#    notice, this list of conditions and the following disclaimer in
#    the documentation and/or other materials provided with the
#    distribution.
#  * Neither the name of pyglet nor the names of its
#    contributors may be used to endorse or promote products
#    derived from this software without specific prior written
#    permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS
# FOR A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE
# COPYRIGHT OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT,
# INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING,
# BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
# LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER
# CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT
# LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN
# ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.
# ----------------------------------------------------------------------------

import os.path, re, sys, glob
import ctypes
import ctypes.util

def _environ_path(name):
    if name in os.environ:
        return os.environ[name].split(":")
    else:
        return []

class LibraryLoader(object):
    def __init__(self):
        self.other_dirs=[]
    
    def load_library(self,libname):
        """Given the name of a library, load it."""
        paths = self.getpaths(libname)
        
        for path in paths:
            if os.path.exists(path):
                return self.load(path)
        
        raise ImportError,"%s not found." % libname
    
    def load(self,path):
        """Given a path to a library, load it."""
        try:
            # Darwin requires dlopen to be called with mode RTLD_GLOBAL instead
            # of the default RTLD_LOCAL.  Without this, you end up with
            # libraries not being loadable, resulting in "Symbol not found"
            # errors
            if sys.platform == 'darwin':
                return ctypes.CDLL(path, ctypes.RTLD_GLOBAL)
            else:
                return ctypes.cdll.LoadLibrary(path)
        except OSError,e:
            raise ImportError,e
    
    def getpaths(self,libname):
        """Return a list of paths where the library might be found."""
        if os.path.isabs(libname):
            yield libname
        
        else:
            for path in self.getplatformpaths(libname):
                yield path
            
            path = ctypes.util.find_library(libname)
            if path: yield path
    
    def getplatformpaths(self, libname):
        return []

# Darwin (Mac OS X)

class DarwinLibraryLoader(LibraryLoader):
    name_formats = ["lib%s.dylib", "lib%s.so", "lib%s.bundle", "%s.dylib",
                "%s.so", "%s.bundle", "%s"]
    
    def getplatformpaths(self,libname):
        if os.path.pathsep in libname:
            names = [libname]
        else:
            names = [format % libname for format in self.name_formats]
        
        for dir in self.getdirs(libname):
            for name in names:
                yield os.path.join(dir,name)
    
    def getdirs(self,libname):
        '''Implements the dylib search as specified in Apple documentation:
        
        http://developer.apple.com/documentation/DeveloperTools/Conceptual/
            DynamicLibraries/Articles/DynamicLibraryUsageGuidelines.html

        Before commencing the standard search, the method first checks
        the bundle's ``Frameworks`` directory if the application is running
        within a bundle (OS X .app).
        '''

        dyld_fallback_library_path = _environ_path("DYLD_FALLBACK_LIBRARY_PATH")
        if not dyld_fallback_library_path:
            dyld_fallback_library_path = [os.path.expanduser('~/lib'),
                                          '/usr/local/lib', '/usr/lib']
        
        dirs = []
        
        if '/' in libname:
            dirs.extend(_environ_path("DYLD_LIBRARY_PATH"))
        else:
            dirs.extend(_environ_path("LD_LIBRARY_PATH"))
            dirs.extend(_environ_path("DYLD_LIBRARY_PATH"))

        dirs.extend(self.other_dirs)
        dirs.append(".")
        
        if hasattr(sys, 'frozen') and sys.frozen == 'macosx_app':
            dirs.append(os.path.join(
                os.environ['RESOURCEPATH'],
                '..',
                'Frameworks'))

        dirs.extend(dyld_fallback_library_path)
        
        return dirs

# Posix

class PosixLibraryLoader(LibraryLoader):
    _ld_so_cache = None
    
    def _create_ld_so_cache(self):
        # Recreate search path followed by ld.so.  This is going to be
        # slow to build, and incorrect (ld.so uses ld.so.cache, which may
        # not be up-to-date).  Used only as fallback for distros without
        # /sbin/ldconfig.
        #
        # We assume the DT_RPATH and DT_RUNPATH binary sections are omitted.

        directories = []
        for name in ("LD_LIBRARY_PATH",
                     "SHLIB_PATH", # HPUX
                     "LIBPATH", # OS/2, AIX
                     "LIBRARY_PATH", # BE/OS
                    ):
            if name in os.environ:
                directories.extend(os.environ[name].split(os.pathsep))
        directories.extend(self.other_dirs)
        directories.append(".")

        try: directories.extend([dir.strip() for dir in open('/etc/ld.so.conf')])
        except IOError: pass

        directories.extend(['/lib', '/usr/lib', '/lib64', '/usr/lib64'])

        cache = {}
        lib_re = re.compile(r'lib(.*)\.s[ol]')
        ext_re = re.compile(r'\.s[ol]$')
        for dir in directories:
            try:
                for path in glob.glob("%s/*.s[ol]*" % dir):
                    file = os.path.basename(path)

                    # Index by filename
                    if file not in cache:
                        cache[file] = path
                    
                    # Index by library name
                    match = lib_re.match(file)
                    if match:
                        library = match.group(1)
                        if library not in cache:
                            cache[library] = path
            except OSError:
                pass

        self._ld_so_cache = cache
    
    def getplatformpaths(self, libname):
        if self._ld_so_cache is None:
            self._create_ld_so_cache()

        result = self._ld_so_cache.get(libname)
        if result: yield result

        path = ctypes.util.find_library(libname)
        if path: yield os.path.join("/lib",path)

# Windows

class _WindowsLibrary(object):
    def __init__(self, path):
        self.cdll = ctypes.cdll.LoadLibrary(path)
        self.windll = ctypes.windll.LoadLibrary(path)

    def __getattr__(self, name):
        try: return getattr(self.cdll,name)
        except AttributeError:
            try: return getattr(self.windll,name)
            except AttributeError:
                raise

class WindowsLibraryLoader(LibraryLoader):
    name_formats = ["%s.dll", "lib%s.dll"]
    
    def load(self, path):
        return _WindowsLibrary(path)
    
    def getplatformpaths(self, libname):
        if os.path.sep not in libname:
            for name in self.name_formats:
                path = ctypes.util.find_library(name % libname)
                if path:
                    yield path

# Platform switching

# If your value of sys.platform does not appear in this dict, please contact
# the Ctypesgen maintainers.

loaderclass = {
    "darwin":   DarwinLibraryLoader,
    "cygwin":   WindowsLibraryLoader,
    "win32":    WindowsLibraryLoader
}

loader = loaderclass.get(sys.platform, PosixLibraryLoader)()

def add_library_search_dirs(other_dirs):
    loader.other_dirs = other_dirs

load_library = loader.load_library

del loaderclass

# End loader

add_library_search_dirs(['/usr/lib'])

# Begin libraries

_libs["SDL_gfx"] = load_library("SDL_gfx")

# 1 libraries
# End libraries

# No modules

Uint8 = c_uint8 # /usr/include/SDL/SDL_stdinc.h: 99

Sint16 = c_int16 # /usr/include/SDL/SDL_stdinc.h: 100

Uint16 = c_uint16 # /usr/include/SDL/SDL_stdinc.h: 101

Uint32 = c_uint32 # /usr/include/SDL/SDL_stdinc.h: 103

# /usr/include/SDL/SDL_video.h: 53
class struct_SDL_Rect(Structure):
    pass

struct_SDL_Rect.__slots__ = [
    'x',
    'y',
    'w',
    'h',
]
struct_SDL_Rect._fields_ = [
    ('x', Sint16),
    ('y', Sint16),
    ('w', Uint16),
    ('h', Uint16),
]

SDL_Rect = struct_SDL_Rect # /usr/include/SDL/SDL_video.h: 53

# /usr/include/SDL/SDL_video.h: 60
class struct_SDL_Color(Structure):
    pass

struct_SDL_Color.__slots__ = [
    'r',
    'g',
    'b',
    'unused',
]
struct_SDL_Color._fields_ = [
    ('r', Uint8),
    ('g', Uint8),
    ('b', Uint8),
    ('unused', Uint8),
]

SDL_Color = struct_SDL_Color # /usr/include/SDL/SDL_video.h: 60

# /usr/include/SDL/SDL_video.h: 66
class struct_SDL_Palette(Structure):
    pass

struct_SDL_Palette.__slots__ = [
    'ncolors',
    'colors',
]
struct_SDL_Palette._fields_ = [
    ('ncolors', c_int),
    ('colors', POINTER(SDL_Color)),
]

SDL_Palette = struct_SDL_Palette # /usr/include/SDL/SDL_video.h: 66

# /usr/include/SDL/SDL_video.h: 91
class struct_SDL_PixelFormat(Structure):
    pass

struct_SDL_PixelFormat.__slots__ = [
    'palette',
    'BitsPerPixel',
    'BytesPerPixel',
    'Rloss',
    'Gloss',
    'Bloss',
    'Aloss',
    'Rshift',
    'Gshift',
    'Bshift',
    'Ashift',
    'Rmask',
    'Gmask',
    'Bmask',
    'Amask',
    'colorkey',
    'alpha',
]
struct_SDL_PixelFormat._fields_ = [
    ('palette', POINTER(SDL_Palette)),
    ('BitsPerPixel', Uint8),
    ('BytesPerPixel', Uint8),
    ('Rloss', Uint8),
    ('Gloss', Uint8),
    ('Bloss', Uint8),
    ('Aloss', Uint8),
    ('Rshift', Uint8),
    ('Gshift', Uint8),
    ('Bshift', Uint8),
    ('Ashift', Uint8),
    ('Rmask', Uint32),
    ('Gmask', Uint32),
    ('Bmask', Uint32),
    ('Amask', Uint32),
    ('colorkey', Uint32),
    ('alpha', Uint8),
]

SDL_PixelFormat = struct_SDL_PixelFormat # /usr/include/SDL/SDL_video.h: 91

# /usr/include/SDL/SDL_video.h: 105
class struct_private_hwdata(Structure):
    pass

# /usr/include/SDL/SDL_video.h: 115
class struct_SDL_BlitMap(Structure):
    pass

# /usr/include/SDL/SDL_video.h: 122
class struct_SDL_Surface(Structure):
    pass

struct_SDL_Surface.__slots__ = [
    'flags',
    'format',
    'w',
    'h',
    'pitch',
    'pixels',
    'offset',
    'hwdata',
    'clip_rect',
    'unused1',
    'locked',
    'map',
    'format_version',
    'refcount',
]
struct_SDL_Surface._fields_ = [
    ('flags', Uint32),
    ('format', POINTER(SDL_PixelFormat)),
    ('w', c_int),
    ('h', c_int),
    ('pitch', Uint16),
    ('pixels', POINTER(None)),
    ('offset', c_int),
    ('hwdata', POINTER(struct_private_hwdata)),
    ('clip_rect', SDL_Rect),
    ('unused1', Uint32),
    ('locked', Uint32),
    ('map', POINTER(struct_SDL_BlitMap)),
    ('format_version', c_uint),
    ('refcount', c_int),
]

SDL_Surface = struct_SDL_Surface # /usr/include/SDL/SDL_video.h: 122

# /usr/include/SDL/SDL_gfxPrimitives.h: 71
if hasattr(_libs['SDL_gfx'], 'pixelColor'):
    pixelColor = _libs['SDL_gfx'].pixelColor
    pixelColor.restype = c_int
    pixelColor.argtypes = [POINTER(SDL_Surface), Sint16, Sint16, Uint32]

# /usr/include/SDL/SDL_gfxPrimitives.h: 72
if hasattr(_libs['SDL_gfx'], 'pixelRGBA'):
    pixelRGBA = _libs['SDL_gfx'].pixelRGBA
    pixelRGBA.restype = c_int
    pixelRGBA.argtypes = [POINTER(SDL_Surface), Sint16, Sint16, Uint8, Uint8, Uint8, Uint8]

# /usr/include/SDL/SDL_gfxPrimitives.h: 76
if hasattr(_libs['SDL_gfx'], 'hlineColor'):
    hlineColor = _libs['SDL_gfx'].hlineColor
    hlineColor.restype = c_int
    hlineColor.argtypes = [POINTER(SDL_Surface), Sint16, Sint16, Sint16, Uint32]

# /usr/include/SDL/SDL_gfxPrimitives.h: 77
if hasattr(_libs['SDL_gfx'], 'hlineRGBA'):
    hlineRGBA = _libs['SDL_gfx'].hlineRGBA
    hlineRGBA.restype = c_int
    hlineRGBA.argtypes = [POINTER(SDL_Surface), Sint16, Sint16, Sint16, Uint8, Uint8, Uint8, Uint8]

# /usr/include/SDL/SDL_gfxPrimitives.h: 81
if hasattr(_libs['SDL_gfx'], 'vlineColor'):
    vlineColor = _libs['SDL_gfx'].vlineColor
    vlineColor.restype = c_int
    vlineColor.argtypes = [POINTER(SDL_Surface), Sint16, Sint16, Sint16, Uint32]

# /usr/include/SDL/SDL_gfxPrimitives.h: 82
if hasattr(_libs['SDL_gfx'], 'vlineRGBA'):
    vlineRGBA = _libs['SDL_gfx'].vlineRGBA
    vlineRGBA.restype = c_int
    vlineRGBA.argtypes = [POINTER(SDL_Surface), Sint16, Sint16, Sint16, Uint8, Uint8, Uint8, Uint8]

# /usr/include/SDL/SDL_gfxPrimitives.h: 86
if hasattr(_libs['SDL_gfx'], 'rectangleColor'):
    rectangleColor = _libs['SDL_gfx'].rectangleColor
    rectangleColor.restype = c_int
    rectangleColor.argtypes = [POINTER(SDL_Surface), Sint16, Sint16, Sint16, Sint16, Uint32]

# /usr/include/SDL/SDL_gfxPrimitives.h: 87
if hasattr(_libs['SDL_gfx'], 'rectangleRGBA'):
    rectangleRGBA = _libs['SDL_gfx'].rectangleRGBA
    rectangleRGBA.restype = c_int
    rectangleRGBA.argtypes = [POINTER(SDL_Surface), Sint16, Sint16, Sint16, Sint16, Uint8, Uint8, Uint8, Uint8]

# /usr/include/SDL/SDL_gfxPrimitives.h: 92
if hasattr(_libs['SDL_gfx'], 'roundedRectangleColor'):
    roundedRectangleColor = _libs['SDL_gfx'].roundedRectangleColor
    roundedRectangleColor.restype = c_int
    roundedRectangleColor.argtypes = [POINTER(SDL_Surface), Sint16, Sint16, Sint16, Sint16, Sint16, Uint32]

# /usr/include/SDL/SDL_gfxPrimitives.h: 93
if hasattr(_libs['SDL_gfx'], 'roundedRectangleRGBA'):
    roundedRectangleRGBA = _libs['SDL_gfx'].roundedRectangleRGBA
    roundedRectangleRGBA.restype = c_int
    roundedRectangleRGBA.argtypes = [POINTER(SDL_Surface), Sint16, Sint16, Sint16, Sint16, Sint16, Uint8, Uint8, Uint8, Uint8]

# /usr/include/SDL/SDL_gfxPrimitives.h: 98
if hasattr(_libs['SDL_gfx'], 'boxColor'):
    boxColor = _libs['SDL_gfx'].boxColor
    boxColor.restype = c_int
    boxColor.argtypes = [POINTER(SDL_Surface), Sint16, Sint16, Sint16, Sint16, Uint32]

# /usr/include/SDL/SDL_gfxPrimitives.h: 99
if hasattr(_libs['SDL_gfx'], 'boxRGBA'):
    boxRGBA = _libs['SDL_gfx'].boxRGBA
    boxRGBA.restype = c_int
    boxRGBA.argtypes = [POINTER(SDL_Surface), Sint16, Sint16, Sint16, Sint16, Uint8, Uint8, Uint8, Uint8]

# /usr/include/SDL/SDL_gfxPrimitives.h: 104
if hasattr(_libs['SDL_gfx'], 'roundedBoxColor'):
    roundedBoxColor = _libs['SDL_gfx'].roundedBoxColor
    roundedBoxColor.restype = c_int
    roundedBoxColor.argtypes = [POINTER(SDL_Surface), Sint16, Sint16, Sint16, Sint16, Sint16, Uint32]

# /usr/include/SDL/SDL_gfxPrimitives.h: 105
if hasattr(_libs['SDL_gfx'], 'roundedBoxRGBA'):
    roundedBoxRGBA = _libs['SDL_gfx'].roundedBoxRGBA
    roundedBoxRGBA.restype = c_int
    roundedBoxRGBA.argtypes = [POINTER(SDL_Surface), Sint16, Sint16, Sint16, Sint16, Sint16, Uint8, Uint8, Uint8, Uint8]

# /usr/include/SDL/SDL_gfxPrimitives.h: 110
if hasattr(_libs['SDL_gfx'], 'lineColor'):
    lineColor = _libs['SDL_gfx'].lineColor
    lineColor.restype = c_int
    lineColor.argtypes = [POINTER(SDL_Surface), Sint16, Sint16, Sint16, Sint16, Uint32]

# /usr/include/SDL/SDL_gfxPrimitives.h: 111
if hasattr(_libs['SDL_gfx'], 'lineRGBA'):
    lineRGBA = _libs['SDL_gfx'].lineRGBA
    lineRGBA.restype = c_int
    lineRGBA.argtypes = [POINTER(SDL_Surface), Sint16, Sint16, Sint16, Sint16, Uint8, Uint8, Uint8, Uint8]

# /usr/include/SDL/SDL_gfxPrimitives.h: 116
if hasattr(_libs['SDL_gfx'], 'aalineColor'):
    aalineColor = _libs['SDL_gfx'].aalineColor
    aalineColor.restype = c_int
    aalineColor.argtypes = [POINTER(SDL_Surface), Sint16, Sint16, Sint16, Sint16, Uint32]

# /usr/include/SDL/SDL_gfxPrimitives.h: 117
if hasattr(_libs['SDL_gfx'], 'aalineRGBA'):
    aalineRGBA = _libs['SDL_gfx'].aalineRGBA
    aalineRGBA.restype = c_int
    aalineRGBA.argtypes = [POINTER(SDL_Surface), Sint16, Sint16, Sint16, Sint16, Uint8, Uint8, Uint8, Uint8]

# /usr/include/SDL/SDL_gfxPrimitives.h: 121
if hasattr(_libs['SDL_gfx'], 'thickLineColor'):
    thickLineColor = _libs['SDL_gfx'].thickLineColor
    thickLineColor.restype = c_int
    thickLineColor.argtypes = [POINTER(SDL_Surface), Sint16, Sint16, Sint16, Sint16, Uint8, Uint32]

# /usr/include/SDL/SDL_gfxPrimitives.h: 123
if hasattr(_libs['SDL_gfx'], 'thickLineRGBA'):
    thickLineRGBA = _libs['SDL_gfx'].thickLineRGBA
    thickLineRGBA.restype = c_int
    thickLineRGBA.argtypes = [POINTER(SDL_Surface), Sint16, Sint16, Sint16, Sint16, Uint8, Uint8, Uint8, Uint8, Uint8]

# /usr/include/SDL/SDL_gfxPrimitives.h: 128
if hasattr(_libs['SDL_gfx'], 'circleColor'):
    circleColor = _libs['SDL_gfx'].circleColor
    circleColor.restype = c_int
    circleColor.argtypes = [POINTER(SDL_Surface), Sint16, Sint16, Sint16, Uint32]

# /usr/include/SDL/SDL_gfxPrimitives.h: 129
if hasattr(_libs['SDL_gfx'], 'circleRGBA'):
    circleRGBA = _libs['SDL_gfx'].circleRGBA
    circleRGBA.restype = c_int
    circleRGBA.argtypes = [POINTER(SDL_Surface), Sint16, Sint16, Sint16, Uint8, Uint8, Uint8, Uint8]

# /usr/include/SDL/SDL_gfxPrimitives.h: 133
if hasattr(_libs['SDL_gfx'], 'arcColor'):
    arcColor = _libs['SDL_gfx'].arcColor
    arcColor.restype = c_int
    arcColor.argtypes = [POINTER(SDL_Surface), Sint16, Sint16, Sint16, Sint16, Sint16, Uint32]

# /usr/include/SDL/SDL_gfxPrimitives.h: 134
if hasattr(_libs['SDL_gfx'], 'arcRGBA'):
    arcRGBA = _libs['SDL_gfx'].arcRGBA
    arcRGBA.restype = c_int
    arcRGBA.argtypes = [POINTER(SDL_Surface), Sint16, Sint16, Sint16, Sint16, Sint16, Uint8, Uint8, Uint8, Uint8]

# /usr/include/SDL/SDL_gfxPrimitives.h: 139
if hasattr(_libs['SDL_gfx'], 'aacircleColor'):
    aacircleColor = _libs['SDL_gfx'].aacircleColor
    aacircleColor.restype = c_int
    aacircleColor.argtypes = [POINTER(SDL_Surface), Sint16, Sint16, Sint16, Uint32]

# /usr/include/SDL/SDL_gfxPrimitives.h: 140
if hasattr(_libs['SDL_gfx'], 'aacircleRGBA'):
    aacircleRGBA = _libs['SDL_gfx'].aacircleRGBA
    aacircleRGBA.restype = c_int
    aacircleRGBA.argtypes = [POINTER(SDL_Surface), Sint16, Sint16, Sint16, Uint8, Uint8, Uint8, Uint8]

# /usr/include/SDL/SDL_gfxPrimitives.h: 145
if hasattr(_libs['SDL_gfx'], 'filledCircleColor'):
    filledCircleColor = _libs['SDL_gfx'].filledCircleColor
    filledCircleColor.restype = c_int
    filledCircleColor.argtypes = [POINTER(SDL_Surface), Sint16, Sint16, Sint16, Uint32]

# /usr/include/SDL/SDL_gfxPrimitives.h: 146
if hasattr(_libs['SDL_gfx'], 'filledCircleRGBA'):
    filledCircleRGBA = _libs['SDL_gfx'].filledCircleRGBA
    filledCircleRGBA.restype = c_int
    filledCircleRGBA.argtypes = [POINTER(SDL_Surface), Sint16, Sint16, Sint16, Uint8, Uint8, Uint8, Uint8]

# /usr/include/SDL/SDL_gfxPrimitives.h: 151
if hasattr(_libs['SDL_gfx'], 'ellipseColor'):
    ellipseColor = _libs['SDL_gfx'].ellipseColor
    ellipseColor.restype = c_int
    ellipseColor.argtypes = [POINTER(SDL_Surface), Sint16, Sint16, Sint16, Sint16, Uint32]

# /usr/include/SDL/SDL_gfxPrimitives.h: 152
if hasattr(_libs['SDL_gfx'], 'ellipseRGBA'):
    ellipseRGBA = _libs['SDL_gfx'].ellipseRGBA
    ellipseRGBA.restype = c_int
    ellipseRGBA.argtypes = [POINTER(SDL_Surface), Sint16, Sint16, Sint16, Sint16, Uint8, Uint8, Uint8, Uint8]

# /usr/include/SDL/SDL_gfxPrimitives.h: 157
if hasattr(_libs['SDL_gfx'], 'aaellipseColor'):
    aaellipseColor = _libs['SDL_gfx'].aaellipseColor
    aaellipseColor.restype = c_int
    aaellipseColor.argtypes = [POINTER(SDL_Surface), Sint16, Sint16, Sint16, Sint16, Uint32]

# /usr/include/SDL/SDL_gfxPrimitives.h: 158
if hasattr(_libs['SDL_gfx'], 'aaellipseRGBA'):
    aaellipseRGBA = _libs['SDL_gfx'].aaellipseRGBA
    aaellipseRGBA.restype = c_int
    aaellipseRGBA.argtypes = [POINTER(SDL_Surface), Sint16, Sint16, Sint16, Sint16, Uint8, Uint8, Uint8, Uint8]

# /usr/include/SDL/SDL_gfxPrimitives.h: 163
if hasattr(_libs['SDL_gfx'], 'filledEllipseColor'):
    filledEllipseColor = _libs['SDL_gfx'].filledEllipseColor
    filledEllipseColor.restype = c_int
    filledEllipseColor.argtypes = [POINTER(SDL_Surface), Sint16, Sint16, Sint16, Sint16, Uint32]

# /usr/include/SDL/SDL_gfxPrimitives.h: 164
if hasattr(_libs['SDL_gfx'], 'filledEllipseRGBA'):
    filledEllipseRGBA = _libs['SDL_gfx'].filledEllipseRGBA
    filledEllipseRGBA.restype = c_int
    filledEllipseRGBA.argtypes = [POINTER(SDL_Surface), Sint16, Sint16, Sint16, Sint16, Uint8, Uint8, Uint8, Uint8]

# /usr/include/SDL/SDL_gfxPrimitives.h: 169
if hasattr(_libs['SDL_gfx'], 'pieColor'):
    pieColor = _libs['SDL_gfx'].pieColor
    pieColor.restype = c_int
    pieColor.argtypes = [POINTER(SDL_Surface), Sint16, Sint16, Sint16, Sint16, Sint16, Uint32]

# /usr/include/SDL/SDL_gfxPrimitives.h: 171
if hasattr(_libs['SDL_gfx'], 'pieRGBA'):
    pieRGBA = _libs['SDL_gfx'].pieRGBA
    pieRGBA.restype = c_int
    pieRGBA.argtypes = [POINTER(SDL_Surface), Sint16, Sint16, Sint16, Sint16, Sint16, Uint8, Uint8, Uint8, Uint8]

# /usr/include/SDL/SDL_gfxPrimitives.h: 176
if hasattr(_libs['SDL_gfx'], 'filledPieColor'):
    filledPieColor = _libs['SDL_gfx'].filledPieColor
    filledPieColor.restype = c_int
    filledPieColor.argtypes = [POINTER(SDL_Surface), Sint16, Sint16, Sint16, Sint16, Sint16, Uint32]

# /usr/include/SDL/SDL_gfxPrimitives.h: 178
if hasattr(_libs['SDL_gfx'], 'filledPieRGBA'):
    filledPieRGBA = _libs['SDL_gfx'].filledPieRGBA
    filledPieRGBA.restype = c_int
    filledPieRGBA.argtypes = [POINTER(SDL_Surface), Sint16, Sint16, Sint16, Sint16, Sint16, Uint8, Uint8, Uint8, Uint8]

# /usr/include/SDL/SDL_gfxPrimitives.h: 183
if hasattr(_libs['SDL_gfx'], 'trigonColor'):
    trigonColor = _libs['SDL_gfx'].trigonColor
    trigonColor.restype = c_int
    trigonColor.argtypes = [POINTER(SDL_Surface), Sint16, Sint16, Sint16, Sint16, Sint16, Sint16, Uint32]

# /usr/include/SDL/SDL_gfxPrimitives.h: 184
if hasattr(_libs['SDL_gfx'], 'trigonRGBA'):
    trigonRGBA = _libs['SDL_gfx'].trigonRGBA
    trigonRGBA.restype = c_int
    trigonRGBA.argtypes = [POINTER(SDL_Surface), Sint16, Sint16, Sint16, Sint16, Sint16, Sint16, Uint8, Uint8, Uint8, Uint8]

# /usr/include/SDL/SDL_gfxPrimitives.h: 189
if hasattr(_libs['SDL_gfx'], 'aatrigonColor'):
    aatrigonColor = _libs['SDL_gfx'].aatrigonColor
    aatrigonColor.restype = c_int
    aatrigonColor.argtypes = [POINTER(SDL_Surface), Sint16, Sint16, Sint16, Sint16, Sint16, Sint16, Uint32]

# /usr/include/SDL/SDL_gfxPrimitives.h: 190
if hasattr(_libs['SDL_gfx'], 'aatrigonRGBA'):
    aatrigonRGBA = _libs['SDL_gfx'].aatrigonRGBA
    aatrigonRGBA.restype = c_int
    aatrigonRGBA.argtypes = [POINTER(SDL_Surface), Sint16, Sint16, Sint16, Sint16, Sint16, Sint16, Uint8, Uint8, Uint8, Uint8]

# /usr/include/SDL/SDL_gfxPrimitives.h: 195
if hasattr(_libs['SDL_gfx'], 'filledTrigonColor'):
    filledTrigonColor = _libs['SDL_gfx'].filledTrigonColor
    filledTrigonColor.restype = c_int
    filledTrigonColor.argtypes = [POINTER(SDL_Surface), Sint16, Sint16, Sint16, Sint16, Sint16, Sint16, Uint32]

# /usr/include/SDL/SDL_gfxPrimitives.h: 196
if hasattr(_libs['SDL_gfx'], 'filledTrigonRGBA'):
    filledTrigonRGBA = _libs['SDL_gfx'].filledTrigonRGBA
    filledTrigonRGBA.restype = c_int
    filledTrigonRGBA.argtypes = [POINTER(SDL_Surface), Sint16, Sint16, Sint16, Sint16, Sint16, Sint16, Uint8, Uint8, Uint8, Uint8]

# /usr/include/SDL/SDL_gfxPrimitives.h: 201
if hasattr(_libs['SDL_gfx'], 'polygonColor'):
    polygonColor = _libs['SDL_gfx'].polygonColor
    polygonColor.restype = c_int
    polygonColor.argtypes = [POINTER(SDL_Surface), POINTER(Sint16), POINTER(Sint16), c_int, Uint32]

# /usr/include/SDL/SDL_gfxPrimitives.h: 202
if hasattr(_libs['SDL_gfx'], 'polygonRGBA'):
    polygonRGBA = _libs['SDL_gfx'].polygonRGBA
    polygonRGBA.restype = c_int
    polygonRGBA.argtypes = [POINTER(SDL_Surface), POINTER(Sint16), POINTER(Sint16), c_int, Uint8, Uint8, Uint8, Uint8]

# /usr/include/SDL/SDL_gfxPrimitives.h: 207
if hasattr(_libs['SDL_gfx'], 'aapolygonColor'):
    aapolygonColor = _libs['SDL_gfx'].aapolygonColor
    aapolygonColor.restype = c_int
    aapolygonColor.argtypes = [POINTER(SDL_Surface), POINTER(Sint16), POINTER(Sint16), c_int, Uint32]

# /usr/include/SDL/SDL_gfxPrimitives.h: 208
if hasattr(_libs['SDL_gfx'], 'aapolygonRGBA'):
    aapolygonRGBA = _libs['SDL_gfx'].aapolygonRGBA
    aapolygonRGBA.restype = c_int
    aapolygonRGBA.argtypes = [POINTER(SDL_Surface), POINTER(Sint16), POINTER(Sint16), c_int, Uint8, Uint8, Uint8, Uint8]

# /usr/include/SDL/SDL_gfxPrimitives.h: 213
if hasattr(_libs['SDL_gfx'], 'filledPolygonColor'):
    filledPolygonColor = _libs['SDL_gfx'].filledPolygonColor
    filledPolygonColor.restype = c_int
    filledPolygonColor.argtypes = [POINTER(SDL_Surface), POINTER(Sint16), POINTER(Sint16), c_int, Uint32]

# /usr/include/SDL/SDL_gfxPrimitives.h: 214
if hasattr(_libs['SDL_gfx'], 'filledPolygonRGBA'):
    filledPolygonRGBA = _libs['SDL_gfx'].filledPolygonRGBA
    filledPolygonRGBA.restype = c_int
    filledPolygonRGBA.argtypes = [POINTER(SDL_Surface), POINTER(Sint16), POINTER(Sint16), c_int, Uint8, Uint8, Uint8, Uint8]

# /usr/include/SDL/SDL_gfxPrimitives.h: 216
if hasattr(_libs['SDL_gfx'], 'texturedPolygon'):
    texturedPolygon = _libs['SDL_gfx'].texturedPolygon
    texturedPolygon.restype = c_int
    texturedPolygon.argtypes = [POINTER(SDL_Surface), POINTER(Sint16), POINTER(Sint16), c_int, POINTER(SDL_Surface), c_int, c_int]

# /usr/include/SDL/SDL_gfxPrimitives.h: 220
if hasattr(_libs['SDL_gfx'], 'filledPolygonColorMT'):
    filledPolygonColorMT = _libs['SDL_gfx'].filledPolygonColorMT
    filledPolygonColorMT.restype = c_int
    filledPolygonColorMT.argtypes = [POINTER(SDL_Surface), POINTER(Sint16), POINTER(Sint16), c_int, Uint32, POINTER(POINTER(c_int)), POINTER(c_int)]

# /usr/include/SDL/SDL_gfxPrimitives.h: 221
if hasattr(_libs['SDL_gfx'], 'filledPolygonRGBAMT'):
    filledPolygonRGBAMT = _libs['SDL_gfx'].filledPolygonRGBAMT
    filledPolygonRGBAMT.restype = c_int
    filledPolygonRGBAMT.argtypes = [POINTER(SDL_Surface), POINTER(Sint16), POINTER(Sint16), c_int, Uint8, Uint8, Uint8, Uint8, POINTER(POINTER(c_int)), POINTER(c_int)]

# /usr/include/SDL/SDL_gfxPrimitives.h: 224
if hasattr(_libs['SDL_gfx'], 'texturedPolygonMT'):
    texturedPolygonMT = _libs['SDL_gfx'].texturedPolygonMT
    texturedPolygonMT.restype = c_int
    texturedPolygonMT.argtypes = [POINTER(SDL_Surface), POINTER(Sint16), POINTER(Sint16), c_int, POINTER(SDL_Surface), c_int, c_int, POINTER(POINTER(c_int)), POINTER(c_int)]

# /usr/include/SDL/SDL_gfxPrimitives.h: 228
if hasattr(_libs['SDL_gfx'], 'bezierColor'):
    bezierColor = _libs['SDL_gfx'].bezierColor
    bezierColor.restype = c_int
    bezierColor.argtypes = [POINTER(SDL_Surface), POINTER(Sint16), POINTER(Sint16), c_int, c_int, Uint32]

# /usr/include/SDL/SDL_gfxPrimitives.h: 229
if hasattr(_libs['SDL_gfx'], 'bezierRGBA'):
    bezierRGBA = _libs['SDL_gfx'].bezierRGBA
    bezierRGBA.restype = c_int
    bezierRGBA.argtypes = [POINTER(SDL_Surface), POINTER(Sint16), POINTER(Sint16), c_int, c_int, Uint8, Uint8, Uint8, Uint8]

# /usr/include/SDL/SDL_gfxPrimitives.h: 234
if hasattr(_libs['SDL_gfx'], 'gfxPrimitivesSetFont'):
    gfxPrimitivesSetFont = _libs['SDL_gfx'].gfxPrimitivesSetFont
    gfxPrimitivesSetFont.restype = None
    gfxPrimitivesSetFont.argtypes = [POINTER(None), Uint32, Uint32]

# /usr/include/SDL/SDL_gfxPrimitives.h: 235
if hasattr(_libs['SDL_gfx'], 'gfxPrimitivesSetFontRotation'):
    gfxPrimitivesSetFontRotation = _libs['SDL_gfx'].gfxPrimitivesSetFontRotation
    gfxPrimitivesSetFontRotation.restype = None
    gfxPrimitivesSetFontRotation.argtypes = [Uint32]

# /usr/include/SDL/SDL_gfxPrimitives.h: 236
if hasattr(_libs['SDL_gfx'], 'characterColor'):
    characterColor = _libs['SDL_gfx'].characterColor
    characterColor.restype = c_int
    characterColor.argtypes = [POINTER(SDL_Surface), Sint16, Sint16, c_char, Uint32]

# /usr/include/SDL/SDL_gfxPrimitives.h: 237
if hasattr(_libs['SDL_gfx'], 'characterRGBA'):
    characterRGBA = _libs['SDL_gfx'].characterRGBA
    characterRGBA.restype = c_int
    characterRGBA.argtypes = [POINTER(SDL_Surface), Sint16, Sint16, c_char, Uint8, Uint8, Uint8, Uint8]

# /usr/include/SDL/SDL_gfxPrimitives.h: 238
if hasattr(_libs['SDL_gfx'], 'stringColor'):
    stringColor = _libs['SDL_gfx'].stringColor
    stringColor.restype = c_int
    stringColor.argtypes = [POINTER(SDL_Surface), Sint16, Sint16, String, Uint32]

# /usr/include/SDL/SDL_gfxPrimitives.h: 239
if hasattr(_libs['SDL_gfx'], 'stringRGBA'):
    stringRGBA = _libs['SDL_gfx'].stringRGBA
    stringRGBA.restype = c_int
    stringRGBA.argtypes = [POINTER(SDL_Surface), Sint16, Sint16, String, Uint8, Uint8, Uint8, Uint8]

# /usr/include/SDL/SDL_gfxPrimitives.h: 47
try:
    SDL_GFXPRIMITIVES_MAJOR = 2
except:
    pass

# /usr/include/SDL/SDL_gfxPrimitives.h: 47
try:
    SDL_GFXPRIMITIVES_MINOR = 0
except:
    pass

# /usr/include/SDL/SDL_gfxPrimitives.h: 47
try:
    SDL_GFXPRIMITIVES_MICRO = 23
except:
    pass

# No inserted files

