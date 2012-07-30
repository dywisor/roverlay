# R overlay --
# Copyright 2006-2012 Gentoo Foundation
# Distributed under the terms of the GNU General Public License v2
import re
from roverlay import strutil

class DepEnv ( object ):

	# excluding A-Z since dep_str_low will be used to find a match
	_NAME = '(?P<name>[a-z0-9_\-/.+-]+)'
	_VER  = '(?P<ver>[0-9._\-]+)'
	# { <, >, ==, <=, >=, =, != } (TODO !=)
	_VERMOD = '(?P<vmod>[<>]|[=<>!]?[=])'

	# FIXME: "boost library (>1.0)" not resolved as >=dev-libs/boost-1.0,
	# regex \s

	V_REGEX_STR = frozenset ( (
		# 'R >= 2.15', 'R >=2.15' etc. (but not 'R>=2.15'!)
		'^{name}\s+{vermod}?\s*{ver}\s*$'.format (
			name=_NAME, vermod=_VERMOD, ver=_VER
		),
		# TODO: merge these regexes: () [] {} (but not (],{), ...)
		# 'R (>= 2.15)', 'R(>=2.15)' etc.
		'^{name}\s*\(\s*{vermod}?\s*{ver}\s*\)$'.format (
			name=_NAME, vermod=_VERMOD, ver=_VER
		),
		# 'R [>= 2.15]', 'R[>=2.15]' etc.
		'^{name}\s*\[\s*{vermod}?\s*{ver}\s*\]$'.format (
			name=_NAME, vermod=_VERMOD, ver=_VER
		),

		# 'R {>= 2.15}', 'R{>=2.15}' etc.
		'^{name}\s*\{{\s*{vermod}?\s*{ver}\s*\}}$'.format (
			name=_NAME, vermod=_VERMOD, ver=_VER
		),
	) )

	VERSION_REGEX = frozenset (
		re.compile ( regex ) for regex in V_REGEX_STR
	)
	FIXVERSION_REGEX = re.compile ( '[_\-]' )
	TRY_ALL_REGEXES  = False

	STATUS_UNDONE       = 1
	STATUS_RESOLVED     = 2
	STATUS_UNRESOLVABLE = 4

	def __init__ ( self, dep_str, deptype_mask ):
		"""Initializes a dependency environment that represents the dependency
		resolution of one entry in the description data of an R package.
		Precalculating most (if not all) data since this object will be passed
		through many dep rules.

		arguments:
		* dep_str -- dependency string at it appears in the description data.
		"""
		self.deptype_mask = deptype_mask
		self.dep_str      = strutil.unquote ( dep_str )
		self.dep_str_low  = self.dep_str.lower()
		self.status       = DepEnv.STATUS_UNDONE
		self.resolved_by  = None

		self.try_all_regexes = self.__class__.TRY_ALL_REGEXES

		self._depsplit()


		# TODO: analyze dep_str:
		#   extract dep name, dep version, useless comments,...

	# --- end of __init__ (...) ---

	def _depsplit ( self ):
		result = list()
		for r in self.__class__.VERSION_REGEX:
			m = r.match ( self.dep_str_low )
			if m is not None:

				version = self.__class__.FIXVERSION_REGEX.sub (
					'.', m.group ( 'ver' )
				)
				# fix versions like ".9" (-> "0.9")
				if version [0] == '.': version = '0' + version

				vmod = m.group ( 'vmod' )
				if vmod == '==' : vmod = '='

				result.append ( dict (
					name             = m.group ( 'name' ),
					version_modifier = vmod,
					version          = version
				) )

				if not self.try_all_regexes: break

		if result:
			self.fuzzy = tuple ( result )
	# --- end of _depsplit (...) ---

	def set_resolved ( self, resolved_by, append=False ):
		"""Marks this DepEnv as resolved with resolved_by as corresponding
		portage package.

		arguments:
		* resolved_by -- resolving portage package
		* append -- whether to append resolved_by or not; NOT IMPLEMENTED
		"""
		if self.resolved_by is None:
			self.resolved_by = resolved_by
		elif append:
			# useful?
			raise Exception ( "appending is not supported..." )
		else:
			raise Exception (
				"dependency is already resolved and append is disabled."
			)

		# add RESOLVED status
		self.status |= DepEnv.STATUS_RESOLVED

	# --- end of set_resolved (...) ---

	def set_unresolvable ( self, force=False ):
		"""Marks this DepEnv as unresolvable.

		arguments:
		force -- force unresolvable status even if this DepEnv
		          is already resolved
		"""
		if force or not self.status & DepEnv.STATUS_RESOLVED:
			self.resolved_by = None
			self.status |= DepEnv.STATUS_UNRESOLVABLE
		else:
			raise Exception ("dependency is already marked as resolved." )

	# --- end of set_unresolvable (...) ---

	def zap ( self ):
		"""Resets the status of this DepEnv and clears out all resolving pkgs."""
		self.status      = DepEnv.STATUS_UNDONE
		self.resolved_by = None

	# --- end of zap (...) ---

	def is_resolved ( self ):
		"""Returns True if this DepEnv is resolved, else false."""
		return bool ( self.status & DepEnv.STATUS_RESOLVED )

	# --- end of is_resolved (...) ---

	def get_result ( self ):
		"""Returns the result of this DepEnv as a tuple
		( original dep str, resolving portage package ) where resolving portage
		package may be None.
		"""
		return ( self.dep_str, self.resolved_by )

	# --- end of get_result (...) ---

	def get_resolved ( self ):
		return self.resolved_by
	# --- end of get_resolved (...) ---
