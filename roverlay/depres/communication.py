# R overlay --
# Copyright 2006-2012 Gentoo Foundation
# Distributed under the terms of the GNU General Public License v2

import logging

from roverlay.depres.depenv import DepEnv

class DependencyResolverListener:

	def __init__ ( self ):
		self.ident = id ( self )

	def notify ( event_type, pkg_env=None, **extra ):
		"""Notify this listener about an event."""
		pass


class DependencyResolverChannel ( DependencyResolverListener ):

	def __init__ ( self, main_resolver, *args ):
		super ( DependencyResolverChannel, self ) . __init__ ()
		self._depres_master = main_resolver

	def close ( self ):
		"""Closes this channel."""
		pass

	def enabled ( self ):
		return True


class EbuildJobChannel ( DependencyResolverChannel ):
	# this channel has a strict control flow:
	#  add deps -> while not done(): "wait" -> if satisfy_request(): collect/lookup

	def __init__ ( self, main_resolver=None, name=None ):
		super ( EbuildJobChannel, self ) . __init__ ( main_resolver )
		self.dep_env_list    = list ()
		self._done           = False
		self._collected_deps = None

		if not name is None:
			self.name = name

	def get_name ( self ):
		return self.name if hasattr ( self, 'name' ) else None



	def depcount ( self ):
		if isinstance ( self.dep_env_list, list ):
			return len ( self.dep_env_list )
		else:
			return -1


	def done ( self ):
		if not self._done:
			self._done = self._depres_master.done (
				self.ident, len ( self.dep_env_list )
			)
		return self._done

	def add_dependency ( self, dep_str ):
		if self._done:
			raise Exception ( "This channel is 'done', it doesn't accept new dependencies." )
		else:
			dep_env = DepEnv ( dep_str )
			self.dep_env_list.append ( dep_env )
			self._depres_master.enqueue ( dep_env, self.ident )

		return None

	def add_dependencies ( self, dep_list ):
		for dep_str in dep_list: self.add_dependency ( dep_str )
		return None

	def satisfy_request ( self, delete_list_if_unresolvable=True ):
		if self._done:
			if self.dep_env_list is None:
				return False

			dep_collected = list()

			for dep_env in self.dep_env_list:
				if dep_env.is_resolved ():
					dep_collected.append ( dep_env.get_result() [1] )
				else:
					if delete_list_if_unresolvable:
						del self.dep_env_list
						self.dep_env_list = None
					return False

			self._collected_deps = dep_collected
			return True

		return False

	def lookup ( self, dep_str ):
		"""Looks up a specific dep str. Use collect_dependencies() for getting
		all dependencies if order doesn't matter.
		"""
		raise Exception ( "TODO" )
		return None

	def collect_dependencies ( self ):
		"""Returns a tuple ( dep str, resolved by )."""
		if self._done:
			logging.critical ( str ( self._collected_deps ) )
			return self._collected_deps
		raise Exception ( "cannot do that" )

	def trigger_run ( self ):
		self._depres_master.run()
