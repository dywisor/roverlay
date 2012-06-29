#!/usr/bin/python3

import sys
import os.path

if len ( sys.argv ) < 2:
	print ( "Usage: %s <deps|dep_file>" % sys.argv[0] )
	exit ( 10 )

if os.path.isfile ( sys.argv[1] ):
	print ( "reading a file" )
	with open ( sys.argv[1], 'r' ) as fh:
		deps = tuple ( x.strip() for x in filter ( None, fh.readlines() ) )
else:
	deps = sys.argv[1:]


from roverlay.recipe.easyresolver import setup as getres
from roverlay.depres.channels     import EbuildJobChannel


R = getres()
c = EbuildJobChannel ( name='chantest' )
R.register_channel ( c )
c.add_dependencies ( deps )


if c.satisfy_request():
	print ( "Success!" )
	print ( str ( c.collect_dependencies() ) )
else:
	print ( "<fail>" )
