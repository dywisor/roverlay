#!/usr/bin/env python3
from sys import exit
from sys import argv as ARGV

if True in ( x in ARGV for x in ( '--help', '-h', '?' ) ):
	print ( '\n'.join ( (
		"usage: %s <pkgs|args>" % ARGV[0],
		"* pkgs ::= [pkg]*",
		"* pkg  ::= <path to package file, relative or absolute",
		"* args ::= [arg]*",
		"* arg  ::= --write|--show|--help",
		"** write ^= write overlay (somewhere in /tmp by default)",
		"** show  ^= print overlay to stdout",
	) ) )
	exit ( 0 )


from roverlay.overlay.creator import OverlayCreator

default_pkg = ( 'examples/packages/seewave_1.6.3.tar.gz', )
SHOW  = False
WRITE = False

pkg_list = list()
for i, x in enumerate ( ARGV ):
	if i == 0:
		pass
	elif x == '--show':
		SHOW = True
	elif x == '--write':
		WRITE = True
	else:
		pkg_list.append ( x )

if len (pkg_list) == 0: pkg_list = default_pkg


o = OverlayCreator()

o.add_package_files ( *pkg_list )
o.can_write_overlay = WRITE
o.run()
if SHOW: o.show_overlay()
o.close ( write=True )

if not ( WRITE or SHOW ):
	print ( "Use '--show' or '--write' if you want ebuild/metadata/Manifest output." )
