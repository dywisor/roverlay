# R Overlay -- helper functions etc.
# Copyright 2006-2012 Gentoo Foundation
# Distributed under the terms of the GNU General Public License v2

import re
import os.path
import logging

import os

from roverlay import config

LOGGER = logging.getLogger ( 'util' )


def get_packageinfo ( filepath ):
	"""Returns some info about the given filepath as dict whose contents are
		the file path, the file name ([as package_file with suffix and]
		as filename with tarball suffix removed), the package name
		and the package_version.

	arguments:
	* filepath --
	"""

	package_file = os.path.basename ( filepath )

	# remove .tar.gz .tar.bz2 etc.
	filename = re.sub (
		config.get ( 'R_PACKAGE.suffix_regex' ) + '$', '', package_file
	)

	package_name, sepa, package_version = filename.partition (
		config.get ( 'R_PACKAGE.name_ver_separator', '_' )
	)

	if not sepa:
		# file name unexpected, tarball extraction will (probably) fail
		LOGGER.error ( "unexpected file name '%s'." % filename )

	return dict (
		filepath        = filepath,
		filename        = filename,
		package_file    = package_file,
		package_name    = package_name,
		#package_origin = ?,
		package_version = package_version,
	)

# --- end of get_packageinfo (...) ---

def get_extra_packageinfo ( package_info, name ):
	return dict (
		PKG_DISTDIR = os.path.dirname ( package_info ['package_file'] ),
		EBUILD_FILE = os.path.join (
			config.get_or_fail ( [ 'OVERLAY', 'dir' ] ),
			config.get_or_fail ( [ 'OVERLAY', 'category' ] ),
			package_info [ 'ebuild_filename'].partition ( '-' ) [0],
			package_info [ 'ebuild_filename'] + ".ebuild"
		)
	) [name]
# --- end of get_extra_packageinfo (...) ---

def pipe_lines ( _pipe, use_filter=False, filter_func=None ):
	lines = _pipe.decode().split ('\n')
	if use_filter:
		return filter ( filter_func, lines )
	else:
		return lines
# --- end of pipe_lines (...) ---


def keepenv ( *to_keep, local_env=None ):
	if local_env is None:
		myenv = dict()
	else:
		myenv = local_env

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
	return myenv if local_env is None else None
# --- end of keepenv (...) ---
