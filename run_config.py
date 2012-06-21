#!/usr/bin/env python3

import sys

ARGV = sys.argv[1:]

from roverlay import config

for c in ARGV:
	print ( "<=== " + c + " ===>" )
	config.loader().load_config ( c )
	print ( ">=== " + c + " ===<" )

conf = config.access()
vis = conf.visualize ( into=sys.stdout )
