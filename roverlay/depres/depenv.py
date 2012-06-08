# R overlay --
# Copyright 2006-2012 Gentoo Foundation
# Distributed under the terms of the GNU General Public License v2


class DepEnv ( object ):

	STATUS_UNDONE       = 1
	STATUS_RESOLVED     = 2
	STATUS_UNRESOLVABLE = 4

	def __init__ ( self, dep_str ):
		"""Initializes a dependency environment that represents the dependency
		resolution of one entry in the description data of an R package.

		arguments:
		* dep_str -- dependency string at it appears in the description data.
		"""
		self.ident       = id ( self )
		self.dep_str     = dep_str
		self.status      = DepEnv.STATUS_UNDONE
		self.resolved_by = None

		# TODO: analyze dep_str: extract dep name, dep version, useless comments,...

	# --- end of __init__ (...) ---

	def set_resolved ( self, resolved_by, append=False ):
		"""Marks this DepEnv as resolved with resolved_by as corresponding portage package.

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
			raise Exception ( "dependency is already resolved and append is disabled." )

		# add RESOLVED status
		self.status |= DepEnv.STATUS_RESOLVED

	# --- end of set_resolved (...) ---

	def set_unresolvable ( self, force=False ):
		"""Marks this DepEnv as unresolvable.

		arguments:
		force -- force unresolvable status even if this DepEnv is already resolved
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
