# R overlay -- roverlay package, util
# -*- coding: utf-8 -*-
# Copyright (C) 2012 André Erdmann <dywi@mailerd.de>
# Distributed under the terms of the GNU General Public License;
# either version 2 of the License, or (at your option) any later version.

"""provides utility functions commonly used"""

__all__= [ 'dodir', 'keepenv', 'sysnop', ]

import os
import logging

LOGGER = logging.getLogger ( 'util' )

def keepenv ( *to_keep ):
	"""Selectively imports os.environ.

	arguments:
	* *to_keep -- env vars to keep

	to_keep  ::= <env_item> [, <env_item>]*
	env_item ::= <env_key> | tuple ( <env_key> [, <env_key>], <fallback> )

	example:
	keepenv (
		( 'PATH', '/bin:/usr/bin' ), ( ( 'USER', 'LOGNAME' ), 'user' ),
		PORTDIR
	)
	keeps PATH (with fallback value if unset), USER/LOGNAME (/w fallback) and
	PORTDIR (only if set).
	"""
	myenv = dict()

	for item in to_keep:
		if ( not isinstance ( item, str ) ) and hasattr ( item, '__iter__' ):
			var      = item [0]
			fallback = item [1]
		else:
			var      = item
			fallback = None

		if isinstance ( var, str ):
			if var in os.environ:
				myenv [var] = os.environ [var]
			elif fallback is not None:
				myenv [var] = fallback
		else:
			varlist = var
			for var in varlist:
				if var in os.environ:
					myenv [var] = os.environ [var]
				elif fallback is not None:
					myenv [var] = fallback

	# -- for
	return myenv
# --- end of keepenv (...) ---

def sysnop ( nop_returns_success=True, format_str=None, old_formatting=False ):
	"""Tries to find a no-op system executable, typically /bin/true or
	/bin/false, depending on whether the operation should succeed or fail.

	arguments:
	* nop_returns_success -- whether the no-op should return success
	                          (/bin/true, /bin/echo) or failure (/bin/false)
	* format_str          -- optional; if set and not None:
	                           also return format_str.format ( nop=<no-op>)
	* old_formatting      -- use old formatting for format_str (str % tuple
	                          instead of str.format ( *tuple ))

	returns: no-op command as tuple, optionally with the formatted string
	         as 2nd element or None if no no-op found
	"""
	if nop_returns_success:
		candidates = ( '/bin/true', '/bin/echo' )
	else:
		candidates = ( '/bin/false' )

	for c in candidates:
		if os.path.isfile ( c ):
			if format_str:
				if not old_formatting:
					return ( c, format_str.format ( nop=c ) )
				else:
					return ( c, format_str % c )
			else:
				return ( c, )

	return None
# --- end of sysnop (...) ---

def dodir ( directory, mkdir_p=False, **makedirs_kw ):
	"""Ensures that a directory exists (by creating it, if necessary).

	arguments:
	* directory     --
	* mkdir_p       -- whether to create all necessary parent directories or not
	                   Defaults to False
	* **makedirs_kw -- keywords args for os.makedirs() (if mkdir_p is True)

	returns: True if directory exists else False
	"""
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
