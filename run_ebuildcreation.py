#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright 2006-2012 Gentoo Foundation
# Distributed under the terms of the GNU General Public License v2

import sys

def me ( msg ):
	sys.stderr.write ("<=== run_ebuildcreation " + msg + " ===>\n" )

me ( "start" )

try:
	from roverlay.ebuildjob import EbuildJob
	from roverlay.ebuildcreator import EbuildCreator

	ec = EbuildCreator ()

	for tarball in sys.argv[1:]:
		sys.stderr.write ( "Adding tarball " + tarball + " to the EbuildCreator.\n" )
		if ec.add_package ( tarball ) is None:
			raise Exception ( "ec.add() returns None, fix that." )

	ec.run ()

	for e in ec.collect_ebuilds ():
		sys.stderr.write ( '\n** ebuild, filename=' + e.suggest_name ( '__undef__' ) + '.ebuild\n' )
		sys.stderr.write ( '[### this is an ebuild: ###]\n' )
		e.show ( sys.stderr )
		sys.stderr.write ( '[### this was an ebuild: ###]\n' )

	me ( "end" )

except Exception as err:
	print ( str ( err ) )
	me ( "failed" )
	raise


