# R Overlay -- config, utility functions
# Copyright 2006-2012 Gentoo Foundation
# Distributed under the terms of the GNU General Public License v2

def get_config_path ( key ):
	"""Creates a config path for key.

	arguments:
	* key --

	"""
	_path = key.split ( '.' ) if isinstance ( key, str ) else key
	if isinstance ( _path, ( list, tuple ) ):
		# config paths are [ CAPSLOCK, CAPSLOCK,.... , lowercase item ]
		return [ x.lower() if x == _path [-1] else x.upper() for x in _path ]
	else:
		return _path
# --- end of get_config_path (...) ---

def unquote ( _str, keep_going=False):
	"""Removes enclosing quotes from a string.

	arguments:
	* _str --
	* keep_going -- remove all enclosing quotes ("'"a"'" -> a)
	"""
	if len ( _str ) < 2: return _str
	chars  = '\"\''

	for c in chars:
		if _str [0] == c and _str [-1] == c:
			return unquote ( _str[1:-1] ) if keep_going else _str[1:-1]

	return _str
# --- end of unquote (...) ---
