#!/usr/bin/python
# -*- coding: utf-8 -*-

import os.path
import glob

from setuptools import setup, find_packages

SCRIPT_DIR = os.path.join ( "bin", "install" )

setup (
   name         = 'R_Overlay',
   version      = "0.3.1",
   description  = 'Automatically generated overlay of R packages (SoC2012)',
   author       = 'Andr\xe9 Erdmann',
   author_email = 'dywi@mailerd.de',
   license      = 'GPLv2+',
   url          = 'http://git.overlays.gentoo.org/gitweb/?p=proj/R_overlay.git;a=summary',
   scripts      = glob.glob ( SCRIPT_DIR + os.path.sep + "?*" ),
   packages     = find_packages ( exclude=[ 'tests', 'tests.*' ] ),
   classifiers  = [
      #'Development Status :: 3 - Alpha',
      'Development Status :: 4 - Beta',
      'Environment :: Console',
      'Intended Audience :: Developers',
      'Intended Audience :: System Administrators',
      'License :: OSI Approved :: GNU General Public License v2 or later (GPLv2+)',
      'Operating System :: POSIX :: Linux',
      'Programming Language :: Python :: 2.7',
      'Programming Language :: Python :: 3',
      'Programming Language :: Unix Shell',
      'Topic :: System :: Software Distribution',
   ],
)
