#!/usr/bin/python
# -*- coding: utf-8 -*-

from setuptools import setup, find_packages

setup (
   name         = 'R_Overlay',
   version      = '0.2.5',
   description  = 'Automatically generated overlay of R packages (SoC2012)',
   author       = 'André Erdmann',
   author_email = 'dywi@mailerd.de',
   license      = 'GPLv2+',
   url          = 'http://git.overlays.gentoo.org/gitweb/?p=proj/R_overlay.git;a=summary',
   entry_points = {
      'console_scripts': [
         'roverlay = roverlay.defaultscript:main_installed',
         'roverlay-sh = roverlay.defaultscript:run_shell_main_installed',
         #'roverlay-exec = roverlay.defaultscript:run_script_main_installed',
         'roverlay-mkconfig = roverlay.config.mkconfig:make_config',
      ]
   },
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
