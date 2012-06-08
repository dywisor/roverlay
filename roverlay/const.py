# R Overlay -- constants
# Copyright 2006-2012 Gentoo Foundation
# Distributed under the terms of the GNU General Public License v2

import copy
import time

_CONSTANTS = dict (
	DESCRIPTION = dict (
		field_separator  = ':',
		comment_char     = '#',
		list_split_regex = '\s*[,;]{1}\s*',
		file_name        = 'DESCRIPTION',
	),
	R_PACKAGE = dict (
		suffix_regex       = '[.](tgz|tbz2|tar|(tar[.](gz|bz2)))',
		name_ver_separator = '_',
	),
	EBUILD = dict (
		indent         = '\t',
		default_header = [	'# Copyright 1999-' + str ( time.gmtime() [0] ) + ' Gentoo Foundation',
									'# Distributed under the terms of the GNU General Public License v2',
									'# $Header: $',
									'',
									'EAPI=4',
									'',
									'inherit R-packages'
								],
	)
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
