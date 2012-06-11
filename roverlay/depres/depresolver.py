# R overlay --
# Copyright 2006-2012 Gentoo Foundation
# Distributed under the terms of the GNU General Public License v2

# todo depres result cache

import logging
import threading

try:
	import queue
except ImportError:
	# python 2
	import Queue as queue


from roverlay               import config
from roverlay.depres        import simpledeprule, communication, events
from roverlay.depres.worker import DepResWorker

#from roverlay.depres.depenv import DepEnv (implicit)

class PseudoAtomicCounter ( object ):
	def __init__ ( self, number=0 ):
		self.nlock   = threading.Lock()
		self._number = number
	# --- end of __init__ (...) ---

	def increment_and_get ( self, step=1 ):
		with self.nlock:
			self._number += step
			ret           = self._number
		return ret
	# --- end of increment_and_get (...) ---

	def get ( self ): return self._number

	def __ge__ ( self, other_int ): return self._number >= other_int
	def __gt__ ( self, other_int ): return self._number >  other_int
	def __le__ ( self, other_int ): return self._number <= other_int
	def __lt__ ( self, other_int ): return self._number <  other_int


class DependencyResolver ( object ):
	"""Main object for dependency resolution."""

	LOGGER = logging.getLogger ( "DependencyResolver" )

	NUMTHREADS = config.get ( "DEPRES.jobcount", 0 )

	def __init__ ( self ):
		"""Initializes a DependencyResolver."""

		# these loggers are temporary helpers
		self.logger              = DependencyResolver.LOGGER
		self.logger_unresolvable = self.logger.getChild ( "UNRESOLVABLE" )
		self.logger_resolved     = self.logger.getChild ( "RESOLVED" )

		self.listenermask = events.ALL
		self.logmask      = events.get_reverse_eventmask (
			'RESOLVED', 'UNRESOLVABLE'
		)

		self.runlock  = threading.Lock()
		self._threads = None

		# the list of registered listener modules
		self.listeners = list ()

		# fifo queue for dep resolution
		#  (threads: could use queue.Queue instead of collections.deque)
		self._depqueue = queue.Queue()

		# the queue of failed dep resolutions
		#  they can either be reinserted into the depqueue
		#  or marked as unresolvable
		self._depqueue_failed = queue.Queue()

		# map: channel identifier -> number of done deps (resolved/unresolvable)
		# this serves two purposes:
		# (a) obviously: the number of resolved deps which is useful for channels
		# (b) the keys of this dict is the list of known channels
		#
		self._depdone = dict ()

		# list of rule pools that have been created from reading files
		self.static_rule_pools = list ()
	# --- end of __init__ (...) ---

	def _sort ( self ):
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
		self._sort()
	# --- end of add_rulepool (...) ---

	def _report_event ( self, event, dep_env=None, pkg_env=None, msg=None ):
		"""Reports an event to the log and listeners.


		arguments:
		* event -- name of the event (RESOLVED etc., use capslock!)
		* dep_env -- dependency env
		* pkg_env -- package env, reserved for future usage

		returns: None (implicit)
		"""
		event_type = events.DEPRES_EVENTS [event]
		if self.logmask & event_type:
			# log this event
			if event_type == events.DEPRES_EVENTS ['RESOLVED']:
				self.logger_resolved.info (
					"'%s' as '%s'" % ( dep_env.dep_str, dep_env.resolved_by )
				)
			elif event_type == events.DEPRES_EVENTS ['UNRESOLVABLE']:
				self.logger_unresolvable.info ( "'%s'" % dep_env.dep_str )
			else:
				# "generic" event, expects that kw msg is set
				self.logger.debug ( "event %s : %s" % ( event, msg ) )
		# --- if

		if self.listenermask & event_type:
			# notify listeners
			for lis in self.listeners:
				lis.notify ( event_type, dep_env=dep_env, pkg_env=pkg_env )

	# --- end of _report_event (...) ---

	def set_logmask ( self, mask ):
		"""Sets the logmask for this DependencyResolver which can be used to
		filter events that would normally go into the log file.
		Useful if a listener module reports such events in an extra file.

		arguments:
		* mask -- new logmask that defines which events are logged

		returns: None (implicit)
		"""
		self.logmask = events.ALL if mask < 0 or mask > events.ALL else mask
	# --- end of set_logmask (...) ---

	def set_listenermask ( self, mask ):
		"""Set the mask for the listener modules. This is totally independent
		from the per-listener mask setting and can be used to filter certain
		events.

		arguments:
		* mask -- new listenermask that defines which events are passed

		returns: None (implicit)
		"""
		self.listenermask = events.ALL if mask < 0 or mask > events.ALL else mask
	# --- end of set_listenermask (...) ---

	def add_listener ( self, listener ):
		"""Adds a listener, which listens to events such as
		"dependency is unresolvable".
		Possible use cases include redirecting such events into a file
		for further parsing.

		arguments:
		* listener --

		returns: None (implicit)
		"""
		self.listeners.append ( listener )
	# --- end of add_listener (...) ---

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
		if channel in self._depdone:
			raise Exception ( "channel is already registered." )

		if channel._depres_master is None:
			channel._depres_master = self

		# register channel and allocate a result counter in depdone
		self._depdone [channel.ident] = PseudoAtomicCounter (0)

		return channel
	# --- end of register_channel (...) ---

	def channel_closed ( self, channel_id ):
		# TODO

		# not removing channel_id's DepEnvs from the queues
		# 'cause this costs time
		del self._depdone [channel_id]
	# --- end of channel_closed (...) ---

	def get_worker ( self, max_dep_resolve=0 ):
		"""Returns a dep resolver worker (thread).
		-- Threading is not implemented, this method is just a reminder.

		arguments:
		* max_dep_resolve -- if > 0 : worker stops after resolving # deps
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
		while not self._depqueue_failed.empty():
			# it has to be guaranteed that no items are removed from
			# _depqueue_failed while calling this method,
			# else Queue.Empty will be raised
			self._depqueue.put ( self._depqueue_failed.get_nowait() )
	# --- end of _queue_previously_failed (...) ---


	def start ( self ):
		"""Tells the resolver to run."""
		if not self.runlock.acquire ( False ):
			# already running
			return True
		# --

		jobcount = DependencyResolver.NUMTHREADS

		if jobcount < 1:
			if jobcount < 0:
				self.logger.warning ( "Running in sequential mode." )
			else:
				self.logger.debug ( "Running in sequential mode." )
			self.thread_run ()
		else:
			self.logger.warning (
				"Running in concurrent mode with %i jobs." % jobcount
			)

			# create threads,
			self._threads = [
				threading.Thread ( target=self.thread_run )
				for n in range (jobcount)
			]
			# run them
			for t in self._threads: t.start()
			# and wait until done
			for t in self._threads: t.join()

			# finally remove them
			del self._threads
			self._threads = None


		# iterate over _depqueue_failed and report unresolved
		while not ( self._depqueue_failed.empty() ):

			channel_id, dep_env = self._depqueue_failed.get_nowait()
			dep_env.set_unresolvable()
			self._depdone [channel_id].increment_and_get()

			self._report_event ( 'UNRESOLVABLE', dep_env )

		self.runlock.release()
	# --- end of start (...) ---

	def thread_run ( self ):
		"""Resolves dependencies (thread target).

		returns: None (implicit)
		"""

		while not self._depqueue.empty():

			try:
				to_resolve    = self._depqueue.get_nowait()
			except queue.Empty:
				# this thread is done when the queue is empty, so this is
				# no error, but just the result of the race condition between
				# queue.empty() and queue.get(False)
				return None

			channel_id, dep_env = to_resolve

			if channel_id in self._depdone:
				# else channel has been closed, drop dep

				self.logger.debug ( "Trying to resolve '%s'." % dep_env.dep_str )

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
					self._depdone [channel_id].increment_and_get()

					self._report_event ( 'RESOLVED', dep_env )
				else:
					self._depqueue_failed.put ( to_resolve )

				"""
				## only useful if new rules can be created
				# new rule found, requeue all previously failed dependency searches
				if have_new_rule:
					self._queue_previously_failed
				"""
			# --- end if channel_id in self._depdone

			self._depqueue.task_done()
		# --- end while



	# --- end of thread_run (...) ---

	def enqueue ( self, dep_env, channel_id ):
		"""Adds a DepEnv to the queue of deps to resolve.

		arguments:
		* dep_env -- to add
		* channel_id -- identifier of the channel associated with the dep_env

		returns: None (implicit)
		"""
		self._depqueue.put ( ( channel_id, dep_env ) )

	# --- end of enqueue (...) ---

	def done ( self, channel_id, numdeps ):
		"""Returns True if channel_id exists in depdone and at least numdeps
		dependencies have been resolved for that channel.

		arguments:
		* channel_id --
		* numdeps --
		"""

		if channel_id in self._depdone:
			return self._depdone [channel_id] >= numdeps
		else:
			return False
	# --- end of done (...) ---

	def close ( self ):
		for lis in self.listeners: lis.close()
		del self.listeners
	# --- end of close (...) ---
