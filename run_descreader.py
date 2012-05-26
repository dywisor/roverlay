#!/usr/bin/env python3
# Copyright 2006-2012 Gentoo Foundation
# Distributed under the terms of the GNU General Public License v2

import sys
sys.stderr.write ( "<=== run_descreader start ===>\n" )

try:
	import roverlay.fileio

	reader = roverlay.fileio.DescriptionReader()

	for tarball in sys.argv[1:]:
		reader.readfile ( tarball )

	print ( "<=== run_descreader end ===>\n" )

except Exception as err:
	print ( str ( err ) )
	print ( "<=== run_descreader failed ===>\n" )
	raise


