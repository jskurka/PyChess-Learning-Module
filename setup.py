#!/usr/bin/env python
# -*- coding: UTF-8 -*-

from imp import load_module, find_module
pychess = load_module("pychess", *find_module("pychess",["lib"]))

from distutils.core import setup
from glob import glob
from os import listdir
from os.path import isdir, isfile
import os
import sys

# To run "setup.py register" change name to "NAME+VERSION_NAME"
# because pychess from another author already exist in pypi.
NAME = "pychess"
VERSION = pychess.VERSION

DESC = "Gnome chess game"

LONG_DESC = """PyChess is a Gtk chess client, originally developed for Gnome, but running well under all other Linux desktops.
(Which we know of, at least). PyChess is 100% python code, from the top of the UI to the bottom of the chess engine, and all code
is licensed under the GNU General Public License.

The goal of PyChess is to provide an advanced chess client for Linux following the Gnome Human Interface Guidelines. The client should be usable
to those new to chess, who just want to play a short game and get back to their work, as well as those who wants to use the computer to further
enhance their play."""

CLASSIFIERS = [
    'Development Status :: 3 - Alpha',
    'Environment :: X11 Applications :: Gnome',
    'Intended Audience :: End Users/Desktop',
    'License :: OSI Approved :: GNU General Public License (GPL)',
    'Operating System :: POSIX',
    'Programming Language :: Python',
    'Topic :: Desktop Environment :: Gnome',
    'Topic :: Games/Entertainment :: Board Games',
    'Natural Language :: Arabic',
    'Natural Language :: Bulgarian',
    'Natural Language :: Catalan',
    'Natural Language :: Czech',
    'Natural Language :: Danish',
    'Natural Language :: Dutch',
    'Natural Language :: English',
    'Natural Language :: Finnish',
    'Natural Language :: French',
    'Natural Language :: German',
    'Natural Language :: Greek',
    'Natural Language :: Hebrew',
    'Natural Language :: Hindi', 
    'Natural Language :: Hungarian',
    'Natural Language :: Italian',
    'Natural Language :: Japanese',
    'Natural Language :: Norwegian',
    'Natural Language :: Persian',
    'Natural Language :: Polish',
    'Natural Language :: Portuguese',
    'Natural Language :: Portuguese (Brazilian)',
    'Natural Language :: Romanian',
    'Natural Language :: Russian',
    'Natural Language :: Slovak',
    'Natural Language :: Spanish',
    'Natural Language :: Swedish',
    'Natural Language :: Turkish',
]

os.chdir(os.path.abspath(os.path.dirname(__file__)))

DATA_FILES = [("share/pychess",
    ["README", "AUTHORS", "ARTISTS", "DOCUMENTERS", "LICENSE", "TRANSLATORS", "open.db"])]

# UI
DATA_FILES += [("share/pychess/glade", glob('glade/*.glade'))]
DATA_FILES += [("share/pychess/glade", glob('glade/*.png'))]
DATA_FILES += [("share/pychess/glade", glob('glade/*.svg'))]
DATA_FILES += [("share/pychess/flags", glob('flags/*.png'))]

# Sidepanel (not a package)
DATA_FILES += [("share/pychess/sidepanel", glob('sidepanel/*.glade'))]
DATA_FILES += [("share/pychess/sidepanel", glob('sidepanel/*.py'))]

# Data
DATA_FILES += [('share/applications', ['pychess.desktop'])]
DATA_FILES += [('share/icons/hicolor/scalable/apps', ['pychess.svg'])]
DATA_FILES += [('share/pixmaps', ['pychess.svg'])]
DATA_FILES += [("share/pychess/sounds", glob('sounds/*.ogg'))]
DATA_FILES += [('share/icons/hicolor/24x24/apps', ['pychess.png'])]
DATA_FILES += [('share/gtksourceview-1.0/language-specs', ['gtksourceview-1.0/language-specs/pgn.lang'])]

# Manpages
DATA_FILES += [('share/man/man1', ['manpages/pychess.1.gz'])]

# Language
pofile = "LC_MESSAGES/pychess"
if sys.platform == "win32":
    argv0_path = os.path.dirname(os.path.abspath(sys.executable))
    sys.path.append(argv0_path + "\\tools\\i18n")
    import msgfmt

for dir in [d for d in listdir("lang") if d.find(".svn") < 0 and isdir("lang/"+d)]:
    if sys.platform == "win32":
        file = "lang/%s/%s" % (dir,pofile)
        msgfmt.make(file+".po", file+".mo")
    else:
        os.popen("msgfmt lang/%s/%s.po -o lang/%s/%s.mo" % (dir,pofile,dir,pofile))
    DATA_FILES += [("share/locale/"+dir+"/LC_MESSAGES", ["lang/"+dir+"/"+pofile+".mo"])]

# Packages

PACKAGES = ["pychess", "pychess.gfx", "pychess.ic", "pychess.ic.managers",
            "pychess.Players", "pychess.Savers", "pychess.System",
            "pychess.Utils", "pychess.Utils.lutils", "pychess.Variants",
			"pychess.widgets", "pychess.widgets.pydock" ]
# Setup

setup (
    name             = NAME,
    version          = VERSION,
    author           = 'Pychess team',
    author_email     = 'pychess-people at googlegroups com',
    maintainer       = 'Thomas Dybdahl Ahle',
    classifiers      = CLASSIFIERS,
    keywords         = 'python gtk chess xboard gnuchess game pgn epd board linux',
    description      = DESC,
    long_description = LONG_DESC,
    license          = 'GPL2',
    url              = 'http://pychess.googlepages.com',
    download_url     = 'http://code.google.com/p/pychess/downloads/list',
    package_dir      = {'': 'lib'},
    packages         = PACKAGES,
    data_files       = DATA_FILES,
    scripts          = ['pychess']
)
