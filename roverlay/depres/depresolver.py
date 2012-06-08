# R overlay --
# Copyright 2006-2012 Gentoo Foundation
# Distributed under the terms of the GNU General Public License v2

import logging

from collections import deque

from roverlay.depres import simpledeprule, communication
#from roverlay.depres.depenv import DepEnv (implicit)

class DependencyResolver ( object ):
	"""Main object for dependency resolution."""

	LOGGER = logging.getLogger ( "DependencyResolver" )

	def __init__ ( self ):
		"""Initializes a DependencyResolver."""

		# these loggers are temporary helpers
		self.logger              = DependencyResolver.LOGGER
		self.logger_unresolvable = self.logger.getChild ( "UNRESOLVABLE" )
		self.logger_resolved     = self.logger.getChild ( "RESOLVED" )

		# these are associative lists "identifier -> listener|channel" and
		#  used to communicate with the resolver or listen to it
		# TODO listeners could be a list
		self.channels  = dict ()
		self.listeners = dict ()

		# fifo queue for dep resolution
		#  (threads: could use queue.Queue instead of collections.deque)
		self._depqueue = deque ()

		# the queue of failed dep resolutions
		#  they can either be reinserted into the depqueue or marked as unresolvable
		self._depqueue_failed = deque ()

		# channel identifier -> number of done (resolved/unresolvable) deps
		self._depdone = dict ()

		# list of rule pools that have been created from reading files
		self.static_rule_pools = list ()
	# --- end of __init__ (...) ---

	def log_unresolvable ( self, dep_env ):
		"""Temporary method that logs the "dep is unresolvable" event."""
		if not dep_env.dep_str:
			self.logger_unresolvable.warning ("'' empty? fix that!" )
		else:
			self.logger_unresolvable.info ( "'%s'" % dep_env.dep_str )
	# --- end of log_unresolvable (...) ---

	def log_resolved ( self, dep_env ):
		"""Temporary method that logs the "dep has been resolved" event."""
		self.logger_resolved.info (
			"'%s' as '%s'" % ( dep_env.dep_str, dep_env.resolved_by )
		)
	# --- end of log_resolved (...) ---

	def sort ( self ):
		"""Sorts the rule pools of this resolver."""
		for pool in self.static_rule_pools: pool.sort()
		poolsort = lambda pool : ( pool.priority, pool.rule_weight )
		self.static_rule_pools.sort ( key=poolsort )
	# --- end of sort (...) ---

	def add_rulepool ( self, rulepool, pool_type=None ):
		"""Adds a (static) rule pool to this resolver.
		Calls self.sort() afterwards.

		arguments:
		* rulepool --
		* pool_type -- ignored.
		"""
		self.static_rule_pools.append ( rulepool )
		self.sort()
		return None
	# --- end of add_rulepool (...) ---

	def _report_event ( self, event, pkg_env=None, **extra ):
		"""Reports an event to the log, channels and listeners."""
		pass
	# --- end of _report_event (...) ---

	def set_logmask ( self, logmask ):
		"""Sets the logmask for this DependencyResolver which can be used to
		filter events that would normally go into the log file.
		Useful if a listener module reports such events in an extra file.

		arguments:
		* logmask -- new logmask
		"""
		pass
	# --- end of set_logmask (...) ---

	# def add_listener ( self, listener ): FIXME
	def add_listener ( self ):
		"""Adds a listener, which listens to events such as
		"dependency is unresolvable". Possible use cases include redirecting
		such events into a file for further parsing.

		arguments:
		* listener_type
		"""
		# broken due to module "outsourcing"
		new_listener = DependencyResolverListener()
		# register the new listener
		self.listeners [new_listener.ident] = new_listener
		return new_listener
	# --- end of add_listener (...) ---

	# FIXME get_channel is not useful when using various channel types
	# FIXME : REMOVE.
	def get_channel ( self, readonly=False ):
		"""Returns a communication channel to the DependencyResolver.
		This channel can be used to _talk_, e.g. queue dependencies for resolution
		and collect the results later.

		arguments:
		* readonly -- whether this channel has write access or not
		"""
		# broken due to module "outsourcing"
		new_channel = DependencyResolverChannel ( self )
		self.channels [new_channel.ident] = new_channel
		return new_channel
	# --- end of get_channel (...) ---

	def register_channel ( self, channel ):
		"""Registers a communication channel with this resolver.
		This channel can then be used to _talk_, e.g. queue dependencies for
		resolution and collect the results later.

		arguments:
		* channel -- channel to be registered
		             automatically sets channel's resolver to self if it is None

		raises: Exception if channels is already registered with this resolver

		returns: channel
		 """
		if channel in self.channels:
			raise Exception ( "channel is already registered." )

		if channel._depres_master is None:
			channel._depres_master = self

		self.channels [channel.ident] = channel

		return channel
	# --- end of register_channel (...) ---

	def get_worker ( self, max_dep_resolve=0 ):
		"""Returns a dep resolver worker (thread).
		-- Threading is not implemented, this method is just a reminder.

		arguments:
		* max_dep_resolve -- if > 0 : worker stops after resolving max_dep_resolve deps
		                     if   0 : worker stops when queue is empty
		                     else   : worker does not stop unless told to do so
		"""
		raise Exception ( "DependencyResolver.get_worker(...) is TODO!" )
	# --- end of get_worker (...) ---

	def _queue_previously_failed ( self ):
		"""Inserts all previously failed dependency lookups into the queue
		again.

		returns: None (implicit)
		"""
		queue_again = self._depqueue_failed
		self._depqueue_failed = deque()
		self._depqueue.extend ( queue_again )
	# --- end of _queue_previously_failed (...) ---

	def run ( self ):
		"""Resolves dependencies.

		returns: None (implicit)
		"""

		# TODO: this method has to be replaced when using threads

		while len ( self._depqueue ):

			to_resolve = self._depqueue.popleft()
			channel_id, dep_env = to_resolve

			self.logger.debug ( "Trying to resolve '%s'." % dep_env.dep_str )

			if not channel_id in self.channels:
				# channel has been closed but did not request a cleanup
				raise Exception ( "dirty queue!" )

			#have_new_rule = False

			# resolved can be None, so use a bool for checking
			resolved    = None
			is_resolved = False

			# search for a match in the rule pools
			for rulepool in self.static_rule_pools:
				result = rulepool.matches ( dep_env )
				if not result is None and result [0] > 0:
					resolved    = result [1]
					is_resolved = True
					break



			if is_resolved:
				dep_env.set_resolved ( resolved, append=False )
				self.log_resolved ( dep_env )
				self._depdone [channel_id] +=1
			else:
				self._depqueue_failed.append ( to_resolve )

			"""
			## only useful if new rules can be created
			# new rule found, queue all previously failed dependency searches again
			if have_new_rule:
				self._queue_previously_failed
			"""
		# --- end while

		# iterate over _depqueue_failed and report unresolved

		while len ( self._depqueue_failed ):

			channel_id, dep_env = self._depqueue_failed.popleft()
			dep_env.set_unresolvable()
			self._depdone [channel_id] += 1

			# TODO: temporary log
			self.log_unresolvable ( dep_env )

	# --- end of run (...) ---

	def enqueue ( self, dep_env, channel_id ):
		"""Adds a DepEnv to the queue of deps to resolve.

		arguments:
		* dep_env -- to add
		* channel_id -- identifier of the channel associated with the dep_env

		returns: None (implicit)
		"""
		self._depqueue.append ( ( channel_id, dep_env ) )
		if not channel_id in self._depdone:
			# allocate a result counter in depdone
			self._depdone [channel_id] = 0

	# --- end of enqueue (...) ---

	def done ( self, channel_id, numdeps ):
		"""Returns True if channel_id exists in depdone and at least numdeps
		dependencies have been resolved for that channel.

		arguments:
		* channel_id --
		* numdeps --
		"""

		if channel_id in self._depdone:
			return bool ( self._depdone [channel_id] >= numdeps )
		else:
			return False
	# --- end of done (...) ---
