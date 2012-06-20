#!/usr/bin/env python3

import os.path
import sys
import logging

import roverlay.static.depres

from roverlay                 import config
from roverlay.packageinfo     import PackageInfo
from roverlay.ebuild.creation import EbuildCreation
from roverlay.overlay         import Overlay
from roverlay.depres          import simpledeprule, listeners

# -- prepare

WRITE_OVERLAY = False
if len ( sys.argv ) > 1:
	if sys.argv [1] == '--write':
		WRITE_OVERLAY = True


# the package used for testing
seewave_f = os.path.abspath ( 'examples/packages/seewave_1.6.3.tar.gz' )
# the overlay dir
overlay_d = "/tmp/R-Overlay_0"
config.access().inject ( "OVERLAY.dir", overlay_d )

# dep resolver setup
resolver = roverlay.static.depres.resolver()
# log everything
resolver.set_logmask ( -1 )

# add simple rules to the resolver
rulepool = simpledeprule.SimpleDependencyRulePool (
	'test pool',
	filepath=os.path.abspath ( 'simple-deprules.conf' ),
	priority=25
)

resolver.add_rulepool ( rulepool )


# eclass files
eclass_list = ( 'R-packages', )
eclass_files = tuple ( os.path.abspath ( os.path.join ( 'eclass', "%s.eclass" % x ) ) for x in eclass_list )

#for e in eclass_files:
#	if not os.path.isfile ( e ):
#		raise Exception ( "eclass %s is missing!" % e )


o = Overlay (
	name="R-packages",
	logger=None,
	directory=None,
	default_category="sci-R",
	eclass_files=eclass_files
)

p = PackageInfo ( filepath=seewave_f )
e = EbuildCreation ( p )

# -- run

e.run()

resolver.close()

if p ['ebuild'] is None:
	sys.stderr.write ( "No ebuild created!\n" )
else:
	try:
		o.add ( p )
		o.show()
		if WRITE_OVERLAY:
			o.write()
			sys.stderr.write ( "Overlay written - directory is '%s'.\n" % overlay_d )
	except Exception as e:
		sys.stderr.write ( "Overlay creation/update failed!\n" )
		raise

