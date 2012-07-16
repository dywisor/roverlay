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
from roverlay.depres import communication, deptype, events
import roverlay.depres.simpledeprule.reader


# if false: do not use the "negative" result caching which stores
# unresolvable deps in a set for should-be faster lookups
USING_DEPRES_CACHE = True

# if True: verify that channels are unique for a resolver instance
SAFE_CHANNEL_IDS = True

class DependencyResolver ( object ):
	"""Main object for dependency resolution."""

	def __init__ ( self, err_queue ):
		"""Initializes a DependencyResolver."""

		self.logger              = logging.getLogger ( self.__class__.__name__ )
		self.logger_unresolvable = self.logger.getChild ( "UNRESOLVABLE" )
		self.logger_resolved     = self.logger.getChild ( "RESOLVED" )

		self.listenermask = events.ALL
		self.logmask      = events.get_reverse_eventmask (
			'RESOLVED', 'UNRESOLVABLE'
		)

		self._jobs = config.get ( "DEPRES.jobcount", 0 )

		# used to lock the run methods,
		self._runlock = threading.Lock()



		if self._jobs > 1:
			# the dep res main thread
			self._mainthread = None
			self._thread_close = False


		self.err_queue = err_queue

		# the list of registered listener modules
		self.listeners = list ()

		# fifo queue for dep resolution
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

		if SAFE_CHANNEL_IDS:
			# this lock is used in register_channel
			self._chanlock       = threading.Lock()
			# this stores all channel ids ever registered to this resolver
			self.all_channel_ids = set()
	# --- end of __init__ (...) ---

	def _sort ( self ):
		"""Sorts the rule pools of this resolver."""
		for pool in self.static_rule_pools: pool.sort()
		poolsort = lambda pool : ( pool.priority, pool.rule_weight )
		self.static_rule_pools.sort ( key=poolsort )
	# --- end of sort (...) ---

	def _reset_unresolvable ( self ):
		if USING_DEPRES_CACHE:
			self._dep_unresolvable.clear()
	# --- end of _reset_unresolvable (...) ---

	def _new_rulepools_added ( self ):
		"""Called after adding new rool pools."""
		self._reset_unresolvable()
		self._sort()
	# --- end of _new_rulepools_added (...) ---

	def get_reader ( self ):
		return roverlay.depres.simpledeprule.reader.SimpleDependencyRuleReader (
			pool_add=self.static_rule_pools.append,
			when_done=self._new_rulepools_added
		)
	# --- end of get_reader (...) ---

	def add_rulepool ( self, rulepool, pool_type=None ):
		"""Adds a (static) rule pool to this resolver.
		Calls self.sort() afterwards.

		arguments:
		* rulepool --
		* pool_type -- ignored.
		"""
		self.static_rule_pools.append ( rulepool )
		self._new_rulepools_added()
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
					"{!r} as {!r}".format ( dep_env.dep_str, dep_env.resolved_by )
				)
			elif event_type == events.DEPRES_EVENTS ['UNRESOLVABLE']:
				self.logger_unresolvable.info ( "{!r}".format ( dep_env.dep_str ) )
			else:
				# "generic" event, expects that kw msg is set
				self.logger.debug ( "event {}: {}".format ( event, msg ) )
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

		raises: Exception if channel is already registered with this resolver

		returns: channel
		 """
		if SAFE_CHANNEL_IDS:
			try:
				self._chanlock.acquire()

				if channel.ident in self.all_channel_ids:
					raise Exception ( "channel id reused!" )
				else:
					self.all_channel_ids.add ( channel.ident )

				# register channel and allocate a queue in depqueue_done
				self._depqueue_done [channel.ident] = queue.Queue()

				channel.set_resolver (
					self, channel_queue=self._depqueue_done [channel.ident]
				)

			finally:
				self._chanlock.release()
		else:
			if channel.ident in self._depqueue_done:
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
		if self._jobs < 2:
			if not self._depqueue.empty():
				self._run_resolver()
			if not self.err_queue.really_empty():
				self.err_queue.unblock_queues()
		else:
			# new resolver threads run async and
			# can be started with an empty depqueue
			if self._runlock.acquire ( False ):
				# else resolver is running

				self._mainthread = threading.Thread (
					target=self._thread_run_resolver
				)
				self._mainthread.start()
				# _thread_run_resolver has to release the lock when done
	# --- end of start (...) ---

	def _process_unresolvable_queue ( self ):
		# iterate over _depqueue_failed and report unresolved
		while not self._depqueue_failed.empty() and self.err_queue.empty:
			try:
				channel_id, dep_env = self._depqueue_failed.get_nowait()
			except queue.Empty:
				# race cond empty() <-> get_nowait()
				return

			dep_env.set_unresolvable()
			self._report_event ( 'UNRESOLVABLE', dep_env )

			try:
				if channel_id in self._depqueue_done:
					self._depqueue_done [channel_id].put_nowait ( dep_env )
			except KeyError:
				# channel has been closed before calling put, ignore this
				pass
	# --- end of _process_unresolvable_queue (...) ---

	def _process_dep ( self, queue_item ):
		channel_id, dep_env = queue_item

		# drop dep if channel closed
		if not channel_id in self._depqueue_done: return

		self.logger.debug (
			"Trying to resolve {!r}.".format ( dep_env.dep_str )
		)

		resolved = None
		# resolved can be None, so use a tri-state int for checking
		#  0 -> unresolved, but resolvable
		#  1 -> unresolved and (currently, new rules may change this)
		#        not resolvable
		#  2 -> resolved
		is_resolved = 0

		if USING_DEPRES_CACHE and dep_env.dep_str_low in self._dep_unresolvable:
			# cannot resolve
			is_resolved = 1

		else:
			# search for a match in the rule pools that accept the dep type
			for rulepool in (
				p for p in self.static_rule_pools \
					if p.deptype_mask & dep_env.deptype_mask
			):
				result = rulepool.matches ( dep_env )
				if result [0] > 0:
					resolved    = result [1]
					is_resolved = 2
					break

			if is_resolved == 0 and dep_env.deptype_mask & deptype.try_other:
				## TRY_OTHER bit is set
				# search for a match in the rule pools
				#  that (normally) don't accept the dep type
				for rulepool in (
					p for p in self.static_rule_pools \
						if p.deptype_mask & ~dep_env.deptype_mask
				):
					result = rulepool.matches ( dep_env )
					if result [0] > 0:
						resolved    = result [1]
						is_resolved = 2
						break
			# --

		# -- done with resolving

		if is_resolved != 2:
			# could not resolve dep_env
			self._depqueue_failed.put ( queue_item )
			if USING_DEPRES_CACHE:
				# does not work when adding new rules is possible
				self._dep_unresolvable.add ( dep_env.dep_str_low )
		else:
			# successfully resolved
			dep_env.set_resolved ( resolved, append=False )
			self._report_event ( 'RESOLVED', dep_env )
			try:
				self._depqueue_done [channel_id].put ( dep_env )
			except KeyError:
				# channel gone while resolving
				pass

			"""
			## only useful if new rules can be created
			# new rule found, requeue all previously
			#  failed dependency searches
			if have_new_rule:
				self._queue_previously_failed
				if USING_DEPRES_CACHE:
					self._dep_unresolvable.clear() #?
			"""
	# --- end of _process_dep (...) ---

	def _run_resolver ( self ):
		# single-threaded variant of run
		#  still checking err_queue 'cause other modules
		#  could be run with threads
		if self._depqueue.empty(): return
		try:
			self._runlock.acquire()
			while not self._depqueue.empty() and self.err_queue.empty:
				to_resolve = self._depqueue.get_nowait()
				self._process_dep ( queue_item=to_resolve )
				self._depqueue.task_done()

			self._process_unresolvable_queue()
		except ( Exception, KeyboardInterrupt ) as e:
			# single-threaded exception catcher:
			# * push exception to inform other threads (if any)
			# * unblock queues (automatically when calling push)
			# * reraise
			self.err_queue.push ( id ( self ), e )
			raise e
		finally:
			self._runlock.release()
	# --- end of _run_resolver (...) ---

	def _thread_run_resolver ( self ):
		"""master thread"""
		try:
			self.logger.debug (
				"Running in concurrent mode with {} worker threads.".format (
					self._jobs
				)
			)
			send_queues = tuple (
				queue.Queue ( maxsize=1 ) for k in range ( self._jobs )
			)
			rec_queues  = tuple (
				queue.Queue ( maxsize=1 ) for k in range ( self._jobs )
			)
			threads = tuple (
				threading.Thread (
					target=self._thread_resolve,
					# this thread's send queue is the worker thread's receive queue
					# and vice versa
					kwargs={ 'recq' : send_queues [n], 'sendq' : rec_queues [n] }
				) for n in range ( self._jobs )
			)

			try:
				for t in threads: t.start()

				# *loop forever*
				# wait for the resolver threads to process the dep queue,
				# mark remaining deps as unresolvable and
				# tell the threads to continue
				while self.err_queue.really_empty() and not self._thread_close:
					for q in rec_queues:
						if q.get() != 0:
							self._thread_close = True
							break
					else:
						self._process_unresolvable_queue()
						# tell the threads to continue
						for q in send_queues: q.put_nowait ( 0 )

			except ( Exception, KeyboardInterrupt ) as e:
				self.err_queue.push ( context=id ( self ), error=e )

			self._thread_close = True

			# on-error code (self.err_queue not empty or close requested)
			try:
				for q in send_queues: q.put_nowait ( 2 )
			except:
				pass

			for t in threads: t.join()

		finally:
			self._runlock.release()
	# --- end of _thread_run_resolver (...) ---

	def _thread_resolve ( self, sendq=0, recq=0 ):
		"""worker thread"""
		try:
			while not self._thread_close and self.err_queue.empty:
				try:
					# process remaining deps
					while not self._thread_close and self.err_queue.empty:
						self._process_dep ( self._depqueue.get_nowait() )
				except queue.Empty:
					pass

				# dep queue has been processed,
				# let the master thread process all unresolvable deps
				# only 0 means continue, anything else stops this thread
				sendq.put_nowait ( 0 )
				if recq.get() != 0: break
		except ( Exception, KeyboardInterrupt ) as e:
			self.err_queue.push ( id ( self ), e )

		# this is on-error code (err_queue is not empty or close requested)
		self._thread_close = True
		try:
			sendq.put_nowait ( 2 )
		except queue.Full:
			pass
	# --- end of _thread_resolve (...) ---

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
		if self._jobs > 1:
			self._thread_close = True
			if self._mainthread:
				self._mainthread.join()
		for lis in self.listeners: lis.close()
		del self.listeners
		if SAFE_CHANNEL_IDS:
			self.logger.debug (
				"{} channels were in use.".format ( len ( self.all_channel_ids ) )
			)
	# --- end of close (...) ---
