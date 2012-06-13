# R overlay --
# Copyright 2006-2012 Gentoo Foundation
# Distributed under the terms of the GNU General Public License v2

import logging
import threading

try:
	import queue
except ImportError:
	# python 2
	import Queue as queue


from roverlay        import config
from roverlay.depres import simpledeprule, communication, events

#from roverlay.depres.depenv import DepEnv (implicit)


# if false: do not using the "negative" result caching which stores
# unresolvable deps in a set for should-be faster lookups
USING_DEPRES_CACHE = True

class DependencyResolver ( object ):
	"""Main object for dependency resolution."""

	LOGGER = logging.getLogger ( "DependencyResolver" )

	NUMTHREADS = config.get ( "DEPRES.jobcount", 2 )

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

		# this lock tells whether a dep res 'master' thread is running (locked)
		self.runlock     = threading.Lock()
		# the dep res main thread
		self._mainthread = None
		# the dep res worker threads
		self._threads    = None


		# the list of registered listener modules
		self.listeners = list ()

		# fifo queue for dep resolution
		#  (threads: could use queue.Queue instead of collections.deque)
		self._depqueue = queue.Queue()

		# the queue of failed dep resolutions
		#  they can either be reinserted into the depqueue
		#  or marked as unresolvable
		self._depqueue_failed = queue.Queue()

		# the 'negative' result cache, stores unresolvable deps
		# has to be (selectively?) cleared when
		# new dep rule found / new rulepool etc.
		if USING_DEPRES_CACHE:
			self._dep_unresolvable = set ()

		# map: channel identifier -> queue of done deps (resolved/unresolvable)
		# this serves two purposes:
		# (a) channels can do a blocking call on this queue
		# (b) the keys of this dict are the list of known channels
		self._depqueue_done = dict ()

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
		if USING_DEPRES_CACHE:
			self._dep_unresolvable.clear()
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
		if channel in self._depqueue_done:
			raise Exception ( "channel is already registered." )

		# register channel and allocate a queue in depqueue_done
		self._depqueue_done [channel.ident] = queue.Queue()

		channel.set_resolver (
			self, channel_queue=self._depqueue_done [channel.ident]
		)

		return channel
	# --- end of register_channel (...) ---

	def channel_closed ( self, channel_id ):
		"""Tells the dependency resolver that a channel has been closed.
		It will then unregister the channel; this operation does not fail if the
		channel is not registered with this resolver.

		arguments:
		* channel_id -- identifier of the closed channel

		returns: None (implicit)
		"""

		# not removing channel_id's DepEnvs from the queues
		# 'cause this costs time
		try:
			del self._depqueue_done [channel_id]
		except KeyError as expected:
			# ok
			pass

	# --- end of channel_closed (...) ---

	def _queue_previously_failed ( self ):
		"""Inserts all previously failed dependency lookups into the queue
		again.

		returns: None (implicit)
		"""
		while not self._depqueue_failed.empty():
			# it has to be guaranteed that no items are removed from
			# _depqueue_failed while calling this method,
			# else queue.Empty will be raised
			self._depqueue.put ( self._depqueue_failed.get_nowait() )
	# --- end of _queue_previously_failed (...) ---

	def start ( self ):
		if not self.runlock.acquire ( False ):
			# already running
			return True
		# --

		if DependencyResolver.NUMTHREADS > 0:
			# no need to wait for the old thread
			self._mainthread = threading.Thread ( target=self._thread_run_main )
			self._mainthread.start()
		else:
			self._thread_run_main()

		# self.runlock is released when _thread_run_main is done
	# --- end of start (...) ---

	def _thread_run_main ( self ):
		"""Tells the resolver to run."""

		jobcount = DependencyResolver.NUMTHREADS

		if jobcount < 1:
			( self.logger.warning if jobcount < 0 else self.logger.debug ) (
				"Running in sequential mode."
			)
			self._thread_run_resolve()
		else:

			# wait for old threads
			if not self._threads is None:
				self.logger.warning ( "Waiting for old threads..." )
				for t in self._threads: t.join()

			self.logger.warning (
				"Running in concurrent mode with %i jobs." % jobcount
			)

			# create threads,
			self._threads = [
				threading.Thread ( target=self._thread_run_resolve )
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
		## todo can thread this
		while not self._depqueue_failed.empty():
			try:
				channel_id, dep_env = self._depqueue_failed.get_nowait()

				dep_env.set_unresolvable()

				self._report_event ( 'UNRESOLVABLE', dep_env )

				if channel_id in self._depqueue_done:
					## todo/fixme/whatever: this 'if' can filter out channels that have
					##  been added again
					self._depqueue_done [channel_id].put ( dep_env )

			except queue.Empty:
				# race cond empty() <-> get_nowait()
				break
			except KeyError:
				# channel has been closed before calling put, ignore this err
				pass

		# release the lock
		self.runlock.release()

	# --- end of _thread_run_main (...) ---

	def _thread_run_resolve ( self ):
		"""Resolves dependencies (thread target).

		returns: None (implicit)
		"""

		while not self._depqueue.empty():

			try:
				to_resolve = self._depqueue.get_nowait()
			except queue.Empty:
				# this thread is done when the queue is empty, so this is
				# no error, but just the result of the race condition between
				# queue.empty() and queue.get(False)
				return None

			channel_id, dep_env = to_resolve

			if channel_id in self._depqueue_done:
				# else channel has been closed, drop dep

				self.logger.debug ( "Trying to resolve '%s'." % dep_env.dep_str )

				#have_new_rule = False

				resolved    = None
				# resolved can be None, so use a tri-state int for checking
				#  0 -> unresolved, but resolvable
				#  1 -> unresolved and (currently, new rules may change this)
				#        not resolvable
				#  2 -> resolved
				is_resolved = 0

				# TODO:
				#  (threading: could search the pools in parallel)

				if USING_DEPRES_CACHE:
					if dep_env.dep_str_low in self._dep_unresolvable:
						# cannot resolve
						is_resolved = 1

				if is_resolved == 0:
					# search for a match in the rule pools
					for rulepool in self.static_rule_pools:
						result = rulepool.matches ( dep_env )
						if not result is None and result [0] > 0:
							resolved    = result [1]
							is_resolved = 2
							break



				if is_resolved == 2:
					dep_env.set_resolved ( resolved, append=False )
					self._report_event ( 'RESOLVED', dep_env )
					self._depqueue_done [channel_id].put ( dep_env )
				else:
					self._depqueue_failed.put ( to_resolve )

					if USING_DEPRES_CACHE:
						# does not work when adding new rules is possible
						self._dep_unresolvable.add ( dep_env.dep_str_low )

				"""
				## only useful if new rules can be created
				# new rule found, requeue all previously failed dependency searches
				if have_new_rule:
					self._queue_previously_failed
					if USING_DEPRES_CACHE:
						self._dep_unresolvable.clear() #?
				"""
			# --- end if channel_id in self._depqueue_done

			self._depqueue.task_done()
		# --- end while



	# --- end of _thread_run_resolve (...) ---

	def enqueue ( self, dep_env, channel_id ):
		"""Adds a DepEnv to the queue of deps to resolve.

		arguments:
		* dep_env -- to add
		* channel_id -- identifier of the channel associated with the dep_env

		returns: None (implicit)
		"""
		self._depqueue.put ( ( channel_id, dep_env ) )

	# --- end of enqueue (...) ---

	def close ( self ):
		if isinstance ( self._mainthread, threading.Thread ):
			self._mainthread.join()
		for lis in self.listeners: lis.close()
		del self.listeners
	# --- end of close (...) ---
