#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright 2006-2012 Gentoo Foundation
# Distributed under the terms of the GNU General Public License v2

import sys
import logging

def me ( msg ):
	sys.stderr.write ("<=== run_ebuildcreation " + msg + " ===>\n" )

me ( "start" )

try:
	from roverlay               import config
	from roverlay.depres        import simpledeprule, listeners
	from roverlay.ebuildjob     import EbuildJob
	from roverlay.ebuildcreator import EbuildCreator

	ec = EbuildCreator ()

	# todo: EbuildCreator should offer a method to load simple rules
	testrules = simpledeprule.SimpleDependencyRulePool (
		'test pool',
		filepath='simple-deprules.conf',
		priority=25
	)
	ec.depresolve_main.add_rulepool ( testrules )
	ec.depresolve_main.set_logmask ( -1 )

	# add listeners
	ec.depresolve_main.add_listener ( listeners.ResolvedFileListener     ( config.get ( 'LOG.FILE.resolved'     ) ) )
	ec.depresolve_main.add_listener ( listeners.UnresolvableFileListener ( config.get ( 'LOG.FILE.unresolvable' ) ) )

	for tarball in sys.argv[1:]:
		sys.stderr.write ( "Adding tarball " + tarball + " to the EbuildCreator.\n" )
		if ec.add_package ( tarball ) is None:
			raise Exception ( "ec.add() returns None, fix that." )

	ec.start()

#	for e in ec.collect_ebuilds ():
#		sys.stderr.write ( '\n** ebuild, filename=' + e.suggest_name ( '__undef__' ) + '.ebuild\n' )
#		sys.stderr.write ( '[### this is an ebuild: ###]\n' )
#		e.show ( sys.stderr )
#		sys.stderr.write ( '[### this was an ebuild: ###]\n' )

	ec.close()

	me ( "end" )

except Exception as err:
	print ( str ( err ) )
	me ( "failed" )
	raise


