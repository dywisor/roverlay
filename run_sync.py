#!/usr/bin/env python3
from sys import exit
from sys import argv as ARGV

if True in ( x in ARGV for x in ( '--help', '-h', '?' ) ):
	print ( '\n'.join ( (
		"usage: %s <args>" % ARGV[0],
		"* args ::= [arg]*",
		"* arg  ::= --write|--show|--help",
		"** write ^= write overlay (somewhere in /tmp by default)",
		"** show  ^= print overlay to stdout",
	) ) )
	exit ( 0 )

import roverlay

from roverlay.overlay.creator import OverlayCreator
from roverlay.remote import RepoList

SHOW  = False
WRITE = False

for i, x in enumerate ( ARGV ):
	if i == 0:
		pass
	elif x == '--show':
		SHOW = True
	elif x == '--write':
		WRITE = True

o = OverlayCreator()
o.can_write_overlay = WRITE

r = RepoList()
r.load()

r.sync()

if not ( WRITE or SHOW ):
	print ( "Use '--show' or '--write' if you want ebuild/metadata/Manifest output." )
