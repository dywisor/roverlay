# R overlay -- config package, const
# -*- coding: utf-8 -*-
# Copyright (C) 2012 André Erdmann <dywi@mailerd.de>
# Distributed under the terms of the GNU General Public License;
# either version 2 of the License, or (at your option) any later version.

"""defines constants"""

import copy
import time

__all__ = [ 'clone', 'lookup' ]

_CONSTANTS = dict (
	DEBUG = False,

	# logging defaults are in recipe/easylogger

	DESCRIPTION = dict (
		field_separator       = ':',
		comment_chars         = '#;',
		list_split_regex      = '\s*[,;]{1}\s*',
		file_name             = 'DESCRIPTION',
	),

	R_PACKAGE = dict (
		suffix_regex       = '[.](tgz|tbz2|tar|(tar[.](gz|bz2)))',
		name_ver_separator = '_',
	),

	EBUILD = dict (
		default_header = '\n'.join ( (
			'# Copyright 1999-%i Gentoo Foundation' % ( time.gmtime() [0] ),
			'# Distributed under the terms of the GNU General Public License v2',
			'# $Header: $',
			'',
			'EAPI=4',
			# inherit <eclasses> is no longer part of the default header
		) ),
	),

	LOG = dict (
		CONSOLE = dict (
			enabled = True,
		),
	),

	OVERLAY = dict (
		name                    = 'R_Overlay',
		category                = 'sci-R',
		manifest_implementation = 'default',
		SYMLINK_DISTROOT        = dict (
			root = "",
			tmp  = True,
		),
	),
)

def lookup ( key, fallback_value=None ):
	"""Looks up a constant. See config.get (...) for details.
	Returns constant if found else None.
	"""
	path = key.split ( '.' )

	const_position = _CONSTANTS

	for k in path:
		if k in const_position:
			const_position = const_position [k]
		else:
			return fallback_value

	return const_position

def clone ( ):
	"""Returns a deep copy of the constants."""
	return copy.deepcopy ( _CONSTANTS )
