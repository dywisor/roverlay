#!/usr/bin/env python
# -*- coding: utf-8 -*-

from distutils import core

VERSION = '0.2'

core.setup (
	name         = 'R_Overlay',
	version      = VERSION,
	description  = 'Automatically generated overlay of R packages (SoC2012)',
	author       = 'André Erdmann',
	author_email = 'dywi@mailerd.de',
	license      = 'GPL',
	url          = 'http://git.overlays.gentoo.org/gitweb/?p=proj/R_overlay.git;a=summary',
	packages     = (
		'roverlay',
		'roverlay/config',
		'roverlay/depres',
		'roverlay/depres/simpledeprule',
		'roverlay/ebuild',
		'roverlay/overlay',
		'roverlay/overlay/manifest',
		'roverlay/overlay/metadata',
		'roverlay/recipe',
		'roverlay/remote',
		'roverlay/rpackage',
	),
)
