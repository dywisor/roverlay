# R overlay -- roverlay package, strutil
# -*- coding: utf-8 -*-
# Copyright (C) 2012 André Erdmann <dywi@mailerd.de>
# Distributed under the terms of the GNU General Public License;
# either version 2 of the License, or (at your option) any later version.

"""provides utility functions for string manipulation"""

__all__ = [ 'ascii_filter', 'fix_ebuild_name',
	'pipe_lines', 'shorten_str', 'unquote'
]

import re

_EBUILD_NAME_ILLEGAL_CHARS = re.compile ( "[.:]{1,}" )
_EBUILD_NAME_ILLEGAL_CHARS_REPLACE_BY = '_'

def fix_ebuild_name ( name ):
	"""Removes illegal chars from an ebuild name by replacing them with an
	underscore char '_'.

	arguments:
	* name --

	returns: string without illegal chars
	"""
	return _EBUILD_NAME_ILLEGAL_CHARS.sub (
		_EBUILD_NAME_ILLEGAL_CHARS_REPLACE_BY,
		name
	)
# --- end of fix_ebuild_name (...) ---

def ascii_filter ( _str ):
	"""Removes all non-ascii chars from a string and returns the result."""
	return ''.join ( c for c in _str if ord ( c ) < 128 )
# --- end of ascii_filter (...) ---

def shorten_str ( s, maxlen, replace_end=None ):
	"""Shortens a string s so that it isn't longer than maxlen chars.
	Optionally replaces the end of a shortened string with another string.
	Does nothing if len(s) <= maxlen.

	arguments:
	* s           --
	* maxlen      --
	* replace_end -- optional; replace the end of a shortened string by this
	                 string (e.g. "abcdefghijk", 6, " (s)" => "ab (s)")

	returns: shortened string
	"""
	if not replace_end is None:
		rlen = maxlen - len ( replace_end )
		if rlen >= 0:
			return s[:rlen] + replace_end if len (s) > maxlen else s

	return s[:maxlen] if len (s) > maxlen else s
# --- end of shorten_str (...) ---

def pipe_lines ( _pipe, use_filter=False, filter_func=None ):
	"""Returns text lines read from a pipe.

	arguments:
	* _pipe       -- pipe to read
	* use_filter  -- whether to use a filter or not. Defaults to False.
	* filter_func -- filter function to use (this can also be 'None')

	returns: text lines
	"""
	lines = _pipe.decode().split ('\n')
	if use_filter:
		return filter ( filter_func, lines )
	else:
		return lines
# --- end of pipe_lines (...) ---

def unquote ( _str, keep_going=False):
	"""Removes enclosing quotes from a string.

	arguments:
	* _str --
	* keep_going -- remove all enclosing quotes ("'"a"'" -> a)
	"""
	if len ( _str ) < 2: return _str
	chars  = '\"\''

	if _str [0] == _str [-1] and _str [0] in chars:
		return unquote ( _str[1:-1] ) if keep_going else _str[1:-1]

	return _str
# --- end of unquote (...) ---
