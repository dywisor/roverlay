# R Overlay -- constants
# Copyright 2006-2012 Gentoo Foundation
# Distributed under the terms of the GNU General Public License v2

import copy
import time

_CONSTANTS = dict (
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
		# indent is currently not in use, FIXME
		#indent         = '\t',
		default_header = '\n'.join ( (
			'# Copyright 1999-%i Gentoo Foundation' % ( time.gmtime() [0] ),
			'# Distributed under the terms of the GNU General Public License v2',
			'# $Header: $',
			'',
			'EAPI=4',
			'',
			# FIXME: don't include eclasses here, calculate their names
			# using OVERLAY.eclass_files
			'inherit R-packages'
		) ),
	),
	OVERLAY = dict (
		category = 'sci-R',
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
