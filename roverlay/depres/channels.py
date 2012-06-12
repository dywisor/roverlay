# R overlay -- dep res channels
# Copyright 2006-2012 Gentoo Foundation
# Distributed under the terms of the GNU General Public License v2

import logging

from roverlay.depres.depenv        import DepEnv
from roverlay.depres.communication import DependencyResolverChannel

COMLINK = logging.getLogger ( "depres.com" )

class EbuildJobChannel ( DependencyResolverChannel ):
	"""The EbuildJobChannel is an interface to the dependency resolver used
	in EbuildJobs.
	It can be used to insert dependency strings, trigger dep resolution,
	poll until done and collect the dependencies afterwards.

	Note that this channel has a strict control flow:
	  add deps, then satisfy_request(): collect/lookup
	"""

	def __init__ ( self, name=None, logger=None ):
		"""EbuildJobChannel

		arguments:
		* name -- name of this channel, optional
		* logger --
		"""
		super ( EbuildJobChannel, self ) . __init__ ( main_resolver=None )

		# this is the number of resolved deps so far, should only be modified
		# in the join()-method
		self._depdone = 0

		# set of portage packages (resolved deps)
		#  this is None unless all deps have been successfully resolved
		self._collected_deps = None

		# used to communicate with the resolver
		self._depres_queue   = None

		# the list of dependency lookups assigned to this channel
		## todo: could remove this list
		self.dep_env_list = list ()

		_logger = logger if hasattr ( logger, 'log' ) else COMLINK
		if name:
			self.name   = name
			self.logger = _logger.getChild ( 'channel.' + name )
		else:
			self.logger = _logger.getChild ( 'channel' )
	# --- end of __init__ (...) ---

	def close ( self ):
		if self._depdone >= 0:
			# else already closed

			super ( EbuildJobChannel, self ) . close()
			del self.dep_env_list, self._collected_deps, self._depres_queue
			del self.logger

			self._depdone = -1
			self._collected_deps = None
	# --- end of close (...) ---

	def set_resolver ( self, resolver, channel_queue, **extra ):
		""" comment todo """
		if self._depres_master is None:
			self._depres_master = resolver
			self._depres_queue  = channel_queue
		else:
			raise Exception ( "channel already bound to a resolver." )
	# --- end of set_resolver (...) ---

	def add_dependency ( self, dep_str ):
		"""Adds a dependency string that should be looked up.
		This channel will create a "dependency environment" for it and enqueues
		that in the dep resolver.

		arguments:
		* dep_str --

		raises: Exception if this channel is done

		returns: None (implicit)
		"""
		if self._depdone:
			raise Exception (
				"This channel is 'done', it doesn't accept new dependencies."
			)
		else:
			dep_env = DepEnv ( dep_str )
			self.dep_env_list.append ( dep_env )
			self._depres_master.enqueue ( dep_env, self.ident )

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

	def lookup ( self, dep_str ):
		"""Looks up a specific dep str. Use the (faster) collect_dependencies()
		method for getting all dependencies if order doesn't matter.

		! It assumes that dep_str is unique in this channel.

		arguments:
		* dep_str -- to be looked up

		raises: Exception if dep_str not in the dep env list.
		"""
		# it's no requirement that this channel is done when calling this method
		for de in self.dep_env_list:
			if de.dep_str == dep_str:
				return de.get_result() [1]

		raise Exception (
			"bad usage: %s not in channel's dep env list!" % dep_str
		)
	# --- end of lookup (...) ---

	def collect_dependencies ( self ):
		"""Returns a list that contains all resolved deps,
		including ignored deps that resolve to None.

		You have to call satisfy_request(...) before using this method.

		raises: Exception
		"""
		if not self._collected_deps is None:
			self.logger.debug (
				"returning collected deps: %s." % self._collected_deps
			)
			return self._collected_deps
		raise Exception ( "cannot do that" )
	# --- end of collect_dependencies (...) ---

	def satisfy_request ( self, close_if_unresolvable=True ):
		"""Tells to the dependency resolver to run.
		It blocks until this channel is done, which means that either all
		deps are resolved or one is unresolvable.

		arguments:
		* close_if_unresolvable -- close the channel if one dep is unresolvable
		                           this seems reasonable and defaults to True

		Returns the list of resolved dependencies if all could be resolved,
		else None.
		"""





		# using a set allows easy difference() operations between
		# DEPEND/RDEPEND/.. later, seewave requires sci-libs/fftw
		# in both DEPEND and RDEPEND for example
		dep_collected = set()

		satisfiable = True

		def handle_queue_item ( dep_env ):
			self._depdone += 1
			if dep_env.is_resolved():
				### and dep_env in self.dep_env_list
				# successfully resolved
				dep_collected.add ( dep_env.get_result() [1] )
			else:
				# failed
				satisfiable = False

			self._depres_queue.task_done()
		# --- end of handle_queue_item (...) ---

		while self._depdone < len ( self.dep_env_list ) and satisfiable:
			# tell the resolver to start
			self._depres_master.start()

			self.logger.critical ( "WAITING..." )

			# wait for one result at least
			handle_queue_item ( self._depres_queue.get() )

			while not self._depres_queue.empty() and satisfiable:
				handle_queue_item ( self._depres_queue.get_nowait() )
		# --- end while

		if satisfiable:
			self._collected_deps = dep_collected
			return self._collected_deps
		else:
			if close_if_unresolvable: self.close()
			return None


	# --- end of join (...) ---
