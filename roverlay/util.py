# R Overlay -- helper functions etc.
# Copyright 2006-2012 Gentoo Foundation
# Distributed under the terms of the GNU General Public License v2

import re
import os
import logging
import threading

from roverlay import config

LOGGER = logging.getLogger ( 'util' )

def easylock ( _lock=threading.Lock() ):
	"""This decorator locks the function while in use
	with either the given Lock or an anonymous threading.Lock.

	arguments:
	* _lock -- lock to use, defaults to threading.Lock()

	returns: wrapped function
	"""
	def wrapper ( f ):
		"""Wraps the function."""
		def _locked ( *args, **kw ):
			"""Actual wrapper.
			Locks _lock, calls the function and releases _lock in any case."""
			try:
				_lock.acquire()
				f ( *args, **kw )
			finally:
				_lock.release()
		return _locked

	return wrapper
# --- end of @easylock (<lock>) ---

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

def get_distdir ( repo_name='' ):
	"""
	Returns the DISTDIR for repo_name or the DISTDIR root if repo_name is empty.

	arguments:
	* repo_name --
	"""

	if len ( repo_name ) > 0:
		distdir = config.get (
			[ 'DISTFILES', 'REPO', repo_name ],
			fallback_value=None
		)
		if distdir is None:
			distdir = os.path.join (
				config.get_or_fail ( [ 'DISTFILES', 'root' ] ),
				repo_name
			)
	else:
		distdir = config.get_or_fail ( [ 'DISTFILES', 'root' ] )

	return distdir


def keepenv ( *to_keep ):
	"""Selectively imports os.environ.

	arguments:
	* *to_keep -- env vars to keep, TODO explain format
	"""
	myenv = dict()

	for item in to_keep:
		if isinstance ( item, tuple ) and len ( item ) == 2:

			var      = item [0]
			fallback = item [1]
		else:
			var      = item
			fallback = None

		if isinstance ( var, str ):
			if var in os.environ:
				myenv [var] = os.environ [var]
			elif not fallback is None:
				myenv [var] = fallback
		else:
			varlist = var
			for var in varlist:
				if var in os.environ:
					myenv [var] = os.environ [var]
				elif not fallback is None:
					myenv [var] = fallback

	# -- for
	return myenv
# --- end of keepenv (...) ---
