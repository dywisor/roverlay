# R Overlay -- helper functions etc.
# Copyright 2006-2012 Gentoo Foundation
# Distributed under the terms of the GNU General Public License v2

import re
import os.path
import logging

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
