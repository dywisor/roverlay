# R overlay -- string utility functions
import re

_EBUILD_NAME_ILLEGAL_CHARS = re.compile ( "[.:]{1,}" )
_EBUILD_NAME_ILLEGAL_CHARS_REPLACE_BY = '_'

def fix_ebuild_name ( name ):
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
	if not replace_end is None:
		rlen = maxlen - len ( replace_end )
		if rlen >= 0:
			return s[:rlen] + replace_end if len (s) > maxlen else s

	return s[:maxlen] if len (s) > maxlen else s
# --- end of shorten_str (...) ---

def pipe_lines ( _pipe, use_filter=False, filter_func=None ):
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
