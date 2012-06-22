# R Overlay -- ebuild construction, ebuild variables
# Copyright 2006-2012 Gentoo Foundation
# Distributed under the terms of the GNU General Public License v2

from roverlay.util import shorten_str

from roverlay.ebuild.abstractcomponents import ListValue, EbuildVar

IUSE_SUGGESTS = 'R_suggests'
RSUGGESTS_NAME = "R_SUGGESTS"

# ignoring case policies here (camel case,..)

class DESCRIPTION ( EbuildVar ):
	"""A DESCRIPTION="..." statement."""
	def __init__ ( self, description, maxlen=50 ):
		"""A DESCRIPTION="..." statement. Long values will be truncated.

		arguments:
		* description -- description text
		* maxlen      -- maximum value length (defaults to 50 chars)
		"""
		super ( DESCRIPTION, self ) . __init__ ( 'DESCRIPTION', description, 80 )
		self.maxlen = 50 if maxlen is None else maxlen

	def __str__ ( self ):
		return '%s%s="%s"' % (
			self.indent,
			self.name,
			shorten_str ( str ( self.value ) , self.maxlen, '... (see metadata)' )
		)


class SRC_URI ( EbuildVar ):
	"""A SRC_URI="..." statement."""
	def __init__ ( self, src_uri ):
		super ( SRC_URI, self ) . __init__ ( 'SRC_URI', src_uri, 90 )


class IUSE ( EbuildVar ):
	"""An IUSE="..." statement."""
	def __init__ ( self, use_flags=None, using_suggests=False ):
		"""An IUSE="..." statement.

		arguments:
		* use_flags      -- IUSE value
		* using_suggests -- if True: enable R_Suggests USE flag
		"""
		super ( IUSE, self ) . __init__ (
			'IUSE',
			ListValue ( use_flags, empty_value='${IUSE:-}' ),
			130
		)
		self.value.single_line = True
		if using_suggests:
			self.value.add ( IUSE_SUGGESTS )


class R_SUGGESTS ( EbuildVar ):
	"""A R_SUGGESTS="..." statement."""
	def __init__ ( self, deps, **kw ):
		super ( R_SUGGESTS, self ) . __init__ (
			RSUGGESTS_NAME,
			ListValue ( deps ),
			140
		)


class DEPEND ( EbuildVar ):
	"""A DEPEND="..." statement."""
	def __init__ ( self, deps, **kw ):
		super ( DEPEND, self ) . __init__ (
			'DEPEND',
			ListValue ( deps ),
			150
		)


class RDEPEND ( EbuildVar ):
	"""A RDEPEND="..." statement."""
	def __init__ ( self, deps, using_suggests=False, **kw ):
		super ( RDEPEND, self ) . __init__ (
			'RDEPEND',
			ListValue ( deps, empty_value="${DEPEND:-}" ),
			160
		)
		if using_suggests: self.enable_suggests()

	def enable_suggests ( self ):
		"""Adds the optional R_SUGGESTS dependencies to RDEPEND."""
		self.value.add ( '%s? ( ${%s} )' % ( IUSE_SUGGESTS, RSUGGESTS_NAME ) )
