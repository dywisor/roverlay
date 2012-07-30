# R Overlay -- helper functions etc.
# Copyright 2006-2012 Gentoo Foundation
# Distributed under the terms of the GNU General Public License v2

import os
import logging

# FIXME: update modules: strutil <> util
from roverlay.strutil import *

LOGGER = logging.getLogger ( 'util' )

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

def sysnop ( nop_returns_success=True, format_str=None ):
	if nop_returns_success:
		candidates = ( '/bin/true', '/bin/echo' )
	else:
		candidates = ( '/bin/false' )

	for c in candidates:
		if os.path.isfile ( c ):
			if format_str:
				return ( c, format_str % c )
			else:
				return ( c, )

	return None
# --- end of sysnop (...) ---

def dodir ( directory, mkdir_p=False, **makedirs_kw ):
	if os.path.isdir ( directory ): return True
	try:
		if mkdir_p:
			os.makedirs ( directory, **makedirs_kw )
		else:
			os.mkdir ( directory )

		return True
	except Exception as e:
		LOGGER.exception ( e )
		return os.path.isdir ( directory )

# --- end of dodir (...) ---
