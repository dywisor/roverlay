#!/usr/bin/python
# This file is part of roverlay
#
#  scans a directory for bad overlay creation results:
#  * empty dirs
#  * missing metadata/Manifest)
#  In contrast to repoman, it does verify that overlay creation succeeded,
#  not that every ebuild is correct.
#
# usage: find_invalid.py <overlay>

import os
import sys

MISSING_METADATA = set()
MISSING_MANIFEST = set()
EMPTY = set()

no_metadata = MISSING_METADATA.add
no_manifest = MISSING_MANIFEST.add
empty       = EMPTY.add

if len ( sys.argv ) != 2:
	sys.stderr.write ( "usage: {} <dir>\n".format ( sys.argv [0] ) )
	sys.exit ( os.EX_USAGE )

topdir = os.path.abspath ( sys.argv [1] )

if not os.path.isdir ( topdir ):
	sys.stderr.write ( "{!r} isn't a directory!\n".format ( topdir ) )
	sys.exit ( os.EX_USAGE )

def ebuild_check ( filenames ):
	man = False
	mtd = False
	eb  = False
	for f in filenames:
		if f.endswith ( '.ebuild' ):
			eb = True

		elif f == 'metadata.xml':
			mtd = True

		elif f == 'Manifest':
			man = True

		if eb and mtd and man:
			return ( True, True, True )

	return ( eb, mtd, man )


for dpath, dnames, fnames in os.walk ( topdir ):
	here = dpath.replace ( topdir, "<overlay root>" )

	e = ebuild_check ( fnames )

	if e[0]:

		if not e[1]:
			# metadata missing
			no_metadata ( here )

		if not e[2]:
			# manifest missing
			no_manifest ( here )

	elif len ( dnames ) == 0 and len ( fnames ) == 0:
		empty ( here )


ALL_OK = not ( MISSING_METADATA or MISSING_MANIFEST or EMPTY )

if MISSING_METADATA:
	print ( "*** The following ebuild directories have no metadata file:" )
	print ( '\n'.join ( sorted ( MISSING_METADATA ) ) )

if MISSING_MANIFEST:
	print ( "*** The following ebuild directories have no Manifest file:" )
	print ( '\n'.join ( sorted ( MISSING_MANIFEST ) ) )

if EMPTY:
	print ( "*** The following dirs are empty:" )
	print ( '\n'.join ( sorted ( EMPTY ) ) )


if ALL_OK:
	print ( "everything looks ok" )
