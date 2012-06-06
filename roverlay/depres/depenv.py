# R overlay --
# Copyright 2006-2012 Gentoo Foundation
# Distributed under the terms of the GNU General Public License v2


class DepEnv:

	STATUS_UNDONE       = 1
	STATUS_RESOLVED     = 2
	STATUS_UNRESOLVABLE = 4

	def __init__ ( self, dep_str ):
		self.ident       = id ( self )
		self.dep_str     = dep_str
		self.status      = DepEnv.STATUS_UNDONE
		self.resolved_by = None

		# TODO: analyze dep_str: extract dep name, dep version, useless comments,...


	def set_resolved ( self, resolved_by, append=False ):
		if self.resolved_by is None:
			self.resolved_by = resolved_by
		elif append:
			raise Exception ( "appending is not supported..." ) #TODO
			#self.resolved_by.append ( resolved_by )
		else:
			raise Exception ( "dependency is already resolved and append is disabled." )

		self.status |= DepEnv.STATUS_RESOLVED

	def set_unresolvable ( self, force=False ):
		if force or not self.status & DepEnv.STATUS_RESOLVED:
			self.resolved_by = None
			self.status |= DepEnv.STATUS_UNRESOLVABLE
		else:
			raise Exception ("dependency is already marked as resolved." )

	def zap ( self ):
		self.status      = DepEnv.STATUS_UNDONE
		self.resolved_by = None

	def is_resolved ( self ):
		return bool ( self.status & DepEnv.STATUS_RESOLVED )

	def get_result ( self ):
		return ( self.dep_str, self.resolved_by )
