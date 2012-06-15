#!/usr/bin/env python3

import logging
import sys

from roverlay.portage.metadata.creation import MetadataJob
from roverlay.portage.metadata.nodes    import *

mj = MetadataJob ( None, logging.getLogger ( 'nop' ) )
m  = mj._metadata

dshort = DescriptionNode ( 'short description', False )
dlong  = DescriptionNode ( 'a longer description\nthat tells you every detail about this package', True )
duse   = UseFlagListNode ()

m.add ( dshort )
m.add ( dlong  )
m.add ( duse )

try:
	duse.add ( NopNode() )
	fail = True
except Exception as e:
	print ( '!!! %s' % e )
	fail = False

if fail: raise Exception ( "bad node accepted!" )

m.get ( 'use' ).add ( UseFlagNode ( 'byte-compile', 'enable byte compiling' ) )
duse.add ( UseFlagNode ( 'R_Suggests', 'install suggested packages' ) )

mj.write ( sys.stdout )
