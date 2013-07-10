#!/usr/bin/python
# -*- coding: utf-8 -*-

import distutils.core

distutils.core.setup (
   name         = 'R_Overlay',
   version      = '0.2.4',
   description  = 'Automatically generated overlay of R packages (SoC2012)',
   author       = 'André Erdmann',
   author_email = 'dywi@mailerd.de',
   license      = 'GPLv2+',
   url          = 'http://git.overlays.gentoo.org/gitweb/?p=proj/R_overlay.git;a=summary',
   packages     = [
      'roverlay'
      'roverlay.config'
      'roverlay.db'
      'roverlay.depres'
      'roverlay.depres.simpledeprule'
      'roverlay.ebuild'
      'roverlay.interface'
      'roverlay.overlay'
      'roverlay.overlay.pkgdir'
      'roverlay.overlay.pkgdir.distroot'
      'roverlay.overlay.pkgdir.manifest'
      'roverlay.overlay.pkgdir.metadata'
      'roverlay.packagerules'
      'roverlay.packagerules.abstract'
      'roverlay.packagerules.acceptors'
      'roverlay.packagerules.actions'
      'roverlay.packagerules.parser'
      'roverlay.packagerules.parser.context'
      'roverlay.recipe'
      'roverlay.remote'
      'roverlay.rpackage'
      'roverlay.tools'
      'roverlay.util'
   ],
   scripts      = [
      'roverlay.py',
   ],
   data_files   = [

   ],
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
