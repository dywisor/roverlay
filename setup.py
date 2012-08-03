#!/usr/bin/env python
# -*- coding: utf-8 -*-

from distutils import core

core.setup (
	name         = 'R_Overlay',
	version      = '0.1',
	description  = 'Automatically generated overlay of R packages (SoC2012)',
	author       = 'André Erdmann',
	author_email = 'dywi@mailerd.de',
	license      = 'GPL-2', #?
	url          = 'http://git.overlays.gentoo.org/gitweb/?p=proj/R_overlay.git;a=summary',
#	py_modules   = ['roverlay'],
	packages     = ( 'roverlay', ),
	scripts      = ( 'roverlay.py', ),
)
