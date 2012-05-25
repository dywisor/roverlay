#!/usr/bin/env python3
# Copyright 2006-2012 Gentoo Foundation
# Distributed under the terms of the GNU General Public License v2

import sys

sys.stderr.write ( "<=== run_ebuildcreation start ===>\n" )

try:
	import roverlay.ebuildcreator

	efac = roverlay.ebuildcreator.EbuildFactory()

	ebuild_creators = []

	for tarball in sys.argv[1:]:
		ec = efac.get_ebuild_creator ( tarball )
		if ec: ebuild_creators.append ( ec )

	for job in ebuild_creators:
		job.run ()

	sys.stderr.write ( "<=== run_ebuildcreation end ===>\n" )

except Error as err:
	sys.stderr.write ( str ( err ) + "\n" )
	sys.stderr.write ( "<=== run_ebuildcreation failed ===>\n" )
