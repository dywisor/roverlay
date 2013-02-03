#!/usr/bin/env python
# -*- coding: utf-8 -*-

from distutils import core

VERSION = '0.2.3'

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
		'roverlay/overlay/pkgdir',
		'roverlay/overlay/pkgdir/manifest',
		'roverlay/overlay/pkgdir/metadata',
		'roverlay/overlay/pkgdir/symlink',
		'roverlay/packagerules',
		'roverlay/packagerules/abstract',
#		'roverlay/packagerules/acceptors',
		'roverlay/packagerules/actions',
#		'roverlay/packagerules/parser',
#		'roverlay/packagerules/parser/context',
		'roverlay/recipe',
		'roverlay/remote',
		'roverlay/rpackage',
	),
)
