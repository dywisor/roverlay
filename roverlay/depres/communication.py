# R overlay --
# Copyright 2006-2012 Gentoo Foundation
# Distributed under the terms of the GNU General Public License v2

import logging

from roverlay.depres.depenv import DepEnv

COMLINK = logging.getLogger ( "depres.com" )

class DependencyResolverListener ( object ):

	def __init__ ( self ):
		"""
		A DependencyResolverListener listens on events sent by the dep resolver.
		It has no access to the resolver, use DependencyResolverChannel for that.
		"""

		# the identifier must be unique and should not be changed after adding
		# the listener to the dep resolver
		self.ident = id ( self )
	# --- end of __init__ (...) ---

	def notify ( self, event_type, pkg_env=None, **extra ):
		"""Notify this listener about an event.

		arguments:
		* event_type --
		* pkg_env --
		* @kw extra --
		"""
		pass
	# --- end of notify (...) ---


class DependencyResolverChannel ( DependencyResolverListener ):

	def __init__ ( self, main_resolver ):
		"""Initializes a DependencyResolverChannel which can be used to
		communicate with the dep resolver.

		arguments:
		* main_resolver -- dep resolver to connect to; setting this to None
		                   results in automatic assignment when registering
		                   with the first dep resolver.
		"""
		super ( DependencyResolverChannel, self ) . __init__ ()
		self._depres_master = main_resolver
	# --- end of __init__ (...) ---

	def close ( self ):
		"""Closes this channel."""
		pass
	# --- end of close (...) ---

	def enabled ( self ):
		"""Returns True if this channel is enabled, else False."""
		return True
	# --- end of enabled (...) ---


class EbuildJobChannel ( DependencyResolverChannel ):
	"""The EbuildJobChannel is an interface to the dependency resolver used
	in EbuildJobs.
	It can be used to insert dependency strings, trigger dep resolution,
	poll until done and collect the dependencies afterwards.

	Note that this channel has a strict control flow:
	add deps -> while not done(): "wait" -> if satisfy_request(): collect/lookup
	"""

	def __init__ ( self, main_resolver=None, name=None ):
		"""EbuildJobChannel

		arguments:
		* main_resolver -- reference to the dep resolver,
		                    optional - dep resolver is automatically assigned
		                    when calling depresolver.register_channel ( $this ).
		* name -- name of this channel, optional
		"""
		super ( EbuildJobChannel, self ) . __init__ ( main_resolver )
		self.dep_env_list    = list ()
		self._done           = False
		self._collected_deps = None

		if name:
			self.name = name
			self.logger = COMLINK.getChild ( 'EbuildJobChannel.' + name )
		else:
			self.logger = COMLINK.getChild ( 'EbuildJobChannel' )
	# --- end of __init__ (...) ---

	def get_name ( self ):
		"""Returns the name of this channel or None if unset."""
		return self.name if hasattr ( self, 'name' ) else None
	# --- end of get_name (...) ---

	def depcount ( self ):
		"""Returns the number of dependency lookups assigned to this channel."""
		if isinstance ( self.dep_env_list, list ):
			return len ( self.dep_env_list )
		else:
			return -1
	# --- end of depcount (...) ---

	def done ( self ):
		"""Returns True if the dep resolver has resolved all deps of this
		channel.
		Note that there is 'no' way back to adding dependencies when/after this
		method returns True.
		"""
		if not self._done:
			self._done = self._depres_master.done (
				self.ident, len ( self.dep_env_list )
			)
		return self._done
	# --- end of done (...) ---

	def add_dependency ( self, dep_str ):
		"""Adds a dependency string that should be looked up.
		This channel will create a "dependency environment" for it and enqueues
		that in the dep resolver.

		arguments:
		* dep_str --

		raises: Exception if this channel is done

		returns: None
		"""
		if self._done:
			raise Exception (
				"This channel is 'done', it doesn't accept new dependencies."
			)
		else:
			dep_env = DepEnv ( dep_str )
			self.dep_env_list.append ( dep_env )
			self._depres_master.enqueue ( dep_env, self.ident )

		return None
	# --- end of add_dependency (...) ---

	def add_dependencies ( self, dep_list ):
		"""Adds dependency strings to this channel. See add_dependency (...)
		for details.

		arguments:
		* dep_list --

		raises: passes Exception if this channel is done

		returns: None (implicit)
		"""
		for dep_str in dep_list: self.add_dependency ( dep_str )
	# --- end of add_dependencies (...) ---

	def satisfy_request ( self, delete_list_if_unresolvable=True ):
		"""Returns True if all dependencies can be satisfied, else False.
		It also prepares the list of resolved dependencies.

		arguments:
		* delete_list_if_unresolvable -- deletes the DepEnv list before
		                                 returning False, else has no effect
		"""

		if self._done:
			if self.dep_env_list is None:
				return False

			# using a set allows easy difference() operations between
			# DEPEND/RDEPEND/.. later, seewave requires sci-libs/fftw
			# in both DEPEND and RDEPEND for example
			dep_collected = set()

			for dep_env in self.dep_env_list:
				if dep_env.is_resolved ():
					dep_collected.add ( dep_env.get_result() [1] )
				else:
					if delete_list_if_unresolvable:
						del self.dep_env_list
						self.dep_env_list = None
					return False

			self._collected_deps = dep_collected
			return True

		return False
	# --- end of satisfy_request (...) ---

	def lookup ( self, dep_str ):
		"""Looks up a specific dep str. Use the (faster) collect_dependencies()
		method for getting all dependencies if order doesn't matter.

		! It assumes that dep_str is unique in this channel.

		arguments:
		* dep_str -- to be looked up

		raises: Exception if dep_str not in the dep env list.
		"""
		for de in self.dep_env_list:
			if de.dep_str == dep_str:
				return de.get_result() [1]

		raise Exception ( "bad usage: %s not in channel's dep env list!" % dep_str )
	# --- end of lookup (...) ---

	def collect_dependencies ( self ):
		"""Returns a list that contains all resolved deps,
		including ignored deps that resolve to None.

		You have to call satisfy_request(...) before using this method.

		raises: Exception
		"""
		if self._done:
			self.logger.debug ( "returning collected deps: " + str ( self._collected_deps ) )
			return self._collected_deps
		raise Exception ( "cannot do that" )
	# --- end of collect_dependencies (...) ---

	def trigger_run ( self ):
		"""Tells the dependency resolver to run.

		returns: None (implicit)
		"""
		self._depres_master.run()
	# --- end of trigger_run (...) ---

	def join ( self ):
		"""Tells to the dependency resolver to run until this channel is done
		(= all deps are done (either resolved or unresolvable)). Blocks.
		"""

		self._done = self._depres_master.done (
			self.ident, len ( self.dep_env_list )
		)
		while not self._done:
			self._depres_master.run()
			self._done = self._depres_master.done (
				self.ident, len ( self.dep_env_list )
			)
	# --- end of join (...) ---
