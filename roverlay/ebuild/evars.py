# R Overlay -- ebuild construction, ebuild variables
# Copyright 2006-2012 Gentoo Foundation
# Distributed under the terms of the GNU General Public License v2

from roverlay import util

from roverlay.ebuild.abstractcomponents import ListValue, EbuildVar

IUSE_SUGGESTS = 'R_suggests'
RSUGGESTS_NAME = IUSE_SUGGESTS.upper()

SEE_METADATA = '... (see metadata)'

# ignoring case policies here (camel case,..)

class DESCRIPTION ( EbuildVar ):
	"""A DESCRIPTION="..." statement."""
	def __init__ ( self, description, maxlen=50 ):
		"""A DESCRIPTION="..." statement. Long values will be truncated.

		arguments:
		* description -- description text
		* maxlen      -- maximum value length (defaults to 50 chars)
		"""
		super ( DESCRIPTION, self ) . __init__ (
			name='DESCRIPTION',
			value=description,
			priority=80, param_expansion=False
		)
		self.maxlen = 50 if maxlen is None else maxlen
		self.use_param_expansion = False

	def _get_value_str ( self ):
		return util.shorten_str (
			util.ascii_filter ( str ( self.value ) ), self.maxlen, SEE_METADATA
		)


class SRC_URI ( EbuildVar ):
	"""A SRC_URI="..." statement."""
	def __init__ ( self, src_uri ):
		super ( SRC_URI, self ) . __init__ (
			name='SRC_URI', value=src_uri, priority=90, param_expansion=False )


class IUSE ( EbuildVar ):
	"""An IUSE="..." statement."""
	def __init__ ( self, use_flags=None, using_suggests=False ):
		"""An IUSE="..." statement.

		arguments:
		* use_flags      -- IUSE value
		* using_suggests -- if True: enable R_Suggests USE flag
		"""
		super ( IUSE, self ) . __init__ (
			name='IUSE',
			value=ListValue ( use_flags, empty_value='${IUSE:-}' ),
			priority=130,
			param_expansion=True
		)
		self.value.single_line = True
		if using_suggests:
			self.value.add ( IUSE_SUGGESTS )


class R_SUGGESTS ( EbuildVar ):
	"""A R_SUGGESTS="..." statement."""
	def __init__ ( self, deps, **kw ):
		super ( R_SUGGESTS, self ) . __init__ (
			name=RSUGGESTS_NAME,
			value=ListValue ( deps ),
			priority=140,
			param_expansion=False
		)


class DEPEND ( EbuildVar ):
	"""A DEPEND="..." statement."""
	def __init__ ( self, deps, **kw ):
		super ( DEPEND, self ) . __init__ (
			name='DEPEND',
			value=ListValue ( deps ),
			priority=150,
			param_expansion=False
		)


class RDEPEND ( EbuildVar ):
	"""A RDEPEND="..." statement."""
	def __init__ ( self, deps, using_suggests=False, **kw ):
		super ( RDEPEND, self ) . __init__ (
			name='RDEPEND',
			value=ListValue ( deps, empty_value="${DEPEND:-}" ),
			priority=160,
			param_expansion=True
		)
		if using_suggests: self.enable_suggests()

	def enable_suggests ( self ):
		"""Adds the optional R_SUGGESTS dependencies to RDEPEND."""
		self.value.add ( '%s? ( ${%s} )' % ( IUSE_SUGGESTS, RSUGGESTS_NAME ) )
