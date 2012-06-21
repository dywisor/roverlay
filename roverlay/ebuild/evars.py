# R Overlay -- ebuild creation, <?>
# Copyright 2006-2012 Gentoo Foundation
# Distributed under the terms of the GNU General Public License v2

from roverlay.util import shorten_str

from roverlay.ebuild.abstractcomponents import ListValue, EbuildVar

IUSE_SUGGESTS = 'R_suggests'
RSUGGESTS_NAME = "R_SUGGESTS"

# ignoring case policies here (camel case,..)

class DESCRIPTION ( EbuildVar ):
	def __init__ ( self, description ):
		super ( DESCRIPTION, self ) . __init__ ( 'DESCRIPTION', description, 80 )

	def __str__ ( self ):
		return '%s%s="%s"' % (
			self.indent,
			self.name,
			shorten_str ( str ( self.value ) , 50, '... (see metadata)' )
		)


class SRC_URI ( EbuildVar ):
	def __init__ ( self, src_uri ):
		super ( SRC_URI, self ) . __init__ ( 'SRC_URI', src_uri, 90 )


class IUSE ( EbuildVar ):
	def __init__ ( self, use_flags=None, using_suggests=False ):
		super ( IUSE, self ) . __init__ (
			'IUSE',
			ListValue ( use_flags, empty_value='${IUSE:-}' ),
			130
		)
		self.value.single_line = True
		if using_suggests:
			self.value.add ( IUSE_SUGGESTS )


class R_SUGGESTS ( EbuildVar ):
	def __init__ ( self, deps, **kw ):
		super ( R_SUGGESTS, self ) . __init__ (
			RSUGGESTS_NAME,
			ListValue ( deps ),
			140
		)


class DEPEND ( EbuildVar ):
	def __init__ ( self, deps, **kw ):
		super ( DEPEND, self ) . __init__ (
			'DEPEND',
			ListValue ( deps ),
			150
		)


class RDEPEND ( EbuildVar ):
	def __init__ ( self, deps, using_suggests=False, **kw ):
		super ( RDEPEND, self ) . __init__ (
			'RDEPEND',
			ListValue ( deps, empty_value="${DEPEND:-}" ),
			160
		)
		if using_suggests: self.enable_suggests()

	def enable_suggests ( self ):
		self.value.add ( '%s? ( ${%s} )' % ( IUSE_SUGGESTS, RSUGGESTS_NAME ) )
