# R overlay -- roverlay package, strutil
# -*- coding: utf-8 -*-
# Copyright (C) 2012 André Erdmann <dywi@mailerd.de>
# Distributed under the terms of the GNU General Public License;
# either version 2 of the License, or (at your option) any later version.

"""provides utility functions for string manipulation"""

__all__ = [ 'ascii_filter', 'bytes_try_decode', 'fix_ebuild_name',
	'pipe_lines', 'shorten_str', 'unquote'
]

import re

_DEFAULT_ENCODINGS = ( 'utf-8', 'ascii', 'iso8859_15', 'utf-16', 'latin_1' )

_EBUILD_NAME_ILLEGAL_CHARS            = re.compile ( "[.:]{1,}" )
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

def bytes_try_decode (
	byte_str,
	encodings=_DEFAULT_ENCODINGS,
	charwise_only=False,
	force_decode=False
):
	"""Tries to decode a bytes object to str whose encoding is unknown
	but predictable (with charwise conversion as last resort).
	Returns byte_str if byte_str is already a str and force_decode is False,
	else a decoded str.

	arguments:
	* byte_str      -- bytes object to decode
	* encodings     -- encodings to try (None, str or list/iterable of str)
	* charwise_only -- do charwise conversion only
	* force_decode  -- decode byte_str even if it's already a str
	"""
	if not isinstance ( byte_str, str ):
		if not charwise_only and encodings:
			ret = None
			if not isinstance ( encodings, str ):
				try_enc = encodings
			else:
				try_enc = ( encodings, )

			for enc in try_enc:
				try:
					ret = byte_str.decode ( enc )
					break
				except:
					ret = None

			if ret is not None:
				return ret

		ret = ""
		for c in byte_str:
			ret += chr ( c )
		return ret
	else:
		return byte_str
# --- end of bytes_try_decode() ---
