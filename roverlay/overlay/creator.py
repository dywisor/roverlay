# R overlay -- overlay package, overlay creation
# -*- coding: utf-8 -*-
# Copyright (C) 2012 André Erdmann <dywi@mailerd.de>
# Distributed under the terms of the GNU General Public License;
# either version 2 of the License, or (at your option) any later version.

"""overlay creation

This module provides the OverlayCreator, a class that handles overlay creation,
which is the remote/R package <-> overlay interface (directly used in the
main script).
"""
__all__ = [ 'OverlayCreator', ]

import collections
import time
import logging
import threading
import sys

try:
	import queue
except ImportError:
	# python2
	import Queue as queue


from roverlay                    import config, errorqueue

from roverlay.overlay            import Overlay
from roverlay.overlay.worker     import OverlayWorker
from roverlay.packageinfo        import PackageInfo
from roverlay.packagerules.rules import PackageRules

from roverlay.recipe             import easyresolver


class PseudoAtomicCounter ( object ):

	def __init__ ( self, start=0, long_int=False ):
		if long_int and sys.version_info < ( 3, 0 ):
			self._value = long ( start )
		else:
			self._value = int ( start )
		self._lock  = threading.Lock()

	def _get_and_inc ( self, step ):
		ret = None
		self._lock.acquire()
		try:
			old_val = self._value
			if step > 0:
				self._value += step
				ret = ( self._value, old_val )
			#elif step < 0: raise...
			else:
				ret = old_val
		finally:
			self._lock.release()

		return ret
	# --- end of _get_and_inc (...) ---

	def inc ( self, step=1 ):
		self._get_and_inc ( step )
	# --- end of inc (...) ---

	def get ( self ):
		return self._get_and_inc ( 0 )
	# --- end of get (...) ---

	def get_nowait ( self ):
		return self._value
	# --- end of get_nowait (...) ---

	def __str__ ( self ):
		return str ( self._value )
	# --- end of __str__ (...) ---


class OverlayCreator ( object ):
	"""This is a 'R packages -> Overlay' interface."""

	LOGGER = logging.getLogger ( 'OverlayCreator' )

	def __init__ ( self,
		skip_manifest, incremental, immediate_ebuild_writes,
		logger=None, allow_write=True
	):
		if logger is None:
			self.logger = self.__class__.LOGGER
		else:
			self.logger = logger.getChild ( 'OverlayCreator' )

		# this queue is used to propagate exceptions from threads
		self._err_queue = errorqueue.ErrorQueue()

		time_scan_overlay = time.time()
		# init overlay using config values
		self.overlay = Overlay.new_configured (
			logger              = self.logger,
			incremental         = incremental,
			write_allowed       = allow_write,
			skip_manifest       = skip_manifest,
			runtime_incremental = immediate_ebuild_writes,
		)
		time_scan_overlay = time.time() - time_scan_overlay

		self.depresolver = easyresolver.setup ( self._err_queue )
		self.depresolver.make_selfdep_pool ( self.overlay.list_rule_kwargs )

		self.package_rules = PackageRules.get_configured()

		self.NUMTHREADS  = config.get ( 'EBUILD.jobcount', 0 )

		self._pkg_queue = queue.Queue()
		self._err_queue.attach_queue ( self._pkg_queue, None )

		#self._time_start_run = list()
		#self._time_stop_run  = list()

		self._workers   = None
		self._runlock   = threading.RLock()

		self.closed = False

		# queued packages counter,
		#  package_added != (create_success + create_fail) if a thread hangs
		#  or did not call _pkg_done
		self.package_added  = PseudoAtomicCounter()

		# counts packages that passed ebuild creation
		self.create_success = PseudoAtomicCounter()

		# counts packages that failed ebuild creation
		self.create_fail    = PseudoAtomicCounter()

		# counts packages that passed adding to overlay
		self.overlay_added  = PseudoAtomicCounter()

		self._timestats     = collections.OrderedDict()

		if incremental and time_scan_overlay >= 0.1:
			self._timestats ['scan_overlay'] = time_scan_overlay

		for k in (
			'sync_packages',
			'add_packages',
			'ebuild_creation',
			'overlay_write',
		):
			self._timestats [k] = -1

	# --- end of __init__ (...) ---

	def set_timestats ( self, name, seconds ):
		self._timestats [name] = seconds
	# --- end of set_timestats (...) ---

	def get_stats ( self ):
		pkg_added   = self.package_added.get_nowait()
		pkg_created = self.create_success.get_nowait()
		pkg_failed  = self.create_fail.get_nowait()
		ov_added    = self.overlay_added.get_nowait()
		ov_failed   = pkg_created - ov_added
		processed   = pkg_created + pkg_failed
		failed      = pkg_failed + ov_failed

		return (
			pkg_added, pkg_created, pkg_failed,
			ov_added, ov_failed,
			processed, failed
		)
	# --- end of get_stats (...) ---

	def stats_str ( self, enclose=True ):
		"""Returns a string with some overlay creation stats."""
		def stats_gen():
			"""Yields stats strings."""
			stats = self.get_stats()

			# the length of the highest number in stats (^=digit count)
			# max_number_len := { 1,...,5 }
			max_number_len = min ( 5, len ( str ( max ( stats ) ) ) )

			for stats_tuple in zip (
				stats,
				(
					'packages added to the ebuild creation queue',
					'packages passed ebuild creation',
					'packages failed ebuild creation',
					'ebuilds could be added to the overlay',
					'ebuilds couldn\'t be added to the overlay',
					'packages processed in total',
					'packages failed in total',
				),
			):
				yield "{num:<{l}} {s}".format (
					num = stats_tuple [0],
					s   = stats_tuple [1],
					l   = max_number_len,
				)

			yield ""

			k_len = min (
				39,
				max ( len ( k ) for k in self._timestats.keys() )
			)

			for k, v in self._timestats.items():
				if v < 0:
					yield "time for {:<{l}} : <unknown>".format ( k, l=k_len, )

				elif v < 1:
					yield "time for {:<{l}} : {} ms".format (
						k,
						round ( v * 1000, 2 ),
						l = k_len,
					)

				elif v > 300:
					yield "time for {:<{l}} : {} minutes".format (
						k,
						round ( v / 60., 2 ),
						l = k_len,
					)

				else:
					yield "time for {}: {} seconds".format ( k, round ( v, 2 ) )
		# --- end of stats_gen (...) ---

		if enclose:
			stats = list ( stats_gen() )

			# maxlen := { 2,...,80 }
			maxlen = 2 + min ( 78,
				len ( max ( stats, key=lambda s : len( s ) ) )
			)

			return (
				"{0:-^{1}}\n".format ( " Overlay creation stats ", maxlen )
				+ '\n'.join ( stats )
				#+ '\n{0:-^{1}}'.format ( '', maxlen )
				+ '\n' + ( maxlen * '-' )
			)

		else:
			return '\n'.join ( stats_gen() )
	# --- end of stats_str (...) ---

	def _timestamp ( self, description, start, stop=None ):
		"""Logs a timestamp, used for testing.

		arguments:
		* description -- timestamp text
		* start       -- when measuring for this timestamp has been started
		* stop        -- stop time; defaults to now (time.time()) if unset
		"""
		_stop = time.time() if stop is None else stop
		delta = _stop - start

		self.logger.debug (
			"timestamp: {} (after {} seconds)".format ( description, delta )
		)
		return delta
	# --- end of _timestamp (...) ---

	def add_package ( self, package_info ):
		"""Adds a PackageInfo to the package queue.

		arguments:
		* package_info --
		"""
		if self.package_rules.apply_actions ( package_info ):
			if self.overlay.add ( package_info ):
				self._pkg_queue.put ( package_info )
				# FIXME package_added is now the # of packages queued for creation
				self.package_added.inc()
		# else filtered out
	# --- end of add_package (...) ---

	def write_overlay ( self ):
		"""Writes the overlay."""
		if self.overlay.writeable():
			start = time.time()
			self.overlay.write()
			self._timestats ['overlay_write'] = (
				self._timestamp ( "overlay written", start )
			)
		else:
			self.logger.warning ( "Not allowed to write overlay!" )
	# --- end of write_overlay (...) ---

	def show_overlay ( self ):
		"""Prints the overlay to the console. Does not create Manifest files."""
		self.overlay.show()
	# --- end of show_overlay (...) ---

	def run ( self, close_when_done=False ):
		"""Starts ebuild creation and waits until done."""
		self._runlock.acquire()
		t_start = time.time()
		try:
			self.start()
			self.join()
		finally:
			self._timestats ['ebuild_creation'] = (
				self._timestamp ( "run() done", t_start )
			)
			self._runlock.release()
			if close_when_done:
				self.close()
	# --- end of run (...) ---

	def start ( self ):
		"""Starts ebuild creation."""
		self._runlock.acquire()
		try:
			self.join()
			self.depresolver.reload_pools()
			self._make_workers()
		except:
			self._err_queue.push ( context=-1, error=None )
			raise
		finally:
			self._runlock.release()
	# --- end of start (...) ---

	def join ( self ):
		"""Waits until ebuild creation is done."""
		self._join_workers()
	# --- end of wait (...) ---

	def close ( self ):
		"""Closes this OverlayCreator."""
		def close_resolver():
			"""Tells the dependency resolver to close.
			This is useful 'cause certain depres listener modules will write files
			when told to exit.
			"""
			if self.depresolver is None: return

			self._runlock.acquire()

			try:
				if self.depresolver is not None:
					self.depresolver.close()
					del self.depresolver
					self.depresolver = None
			finally:
				self._runlock.release()
		# --- end of close_resolver (...) ---

		self._close_workers()
		close_resolver()
		self.closed = True
	# --- end of close (...) ---

	def _waitfor_workers ( self, do_close ):
		"""Waits until the workers are done.

		arguments:
		* do_close -- close (exit) workers if True, else wait until done.
		"""

		if self._workers is None: return
		start = None
		self._runlock.acquire()

		try:
			if self._workers is not None:
				if self.NUMTHREADS > 0: start = time.time()

				if do_close:
					self._err_queue.push ( context=-1, error=None )
					for w in self._workers: w.enabled = False
				else:
					for w in self._workers: w.stop_when_empty()

				while True in ( w.active() for w in self._workers ):
					self._pkg_queue.put ( None )

				del self._workers
				self._workers = None

				for e in self._err_queue.get_exceptions():
					self.logger.warning ( "Reraising thread exception." )
					raise e [1]


		except ( Exception, KeyboardInterrupt ) as err:
			# catch interrupt here: still wait until all workers have been closed
			# and reraise after that
#			SIGINT_RESTORE = signal.signal (
#				signal.SIGINT,
#				lambda sig, frame : sys.stderr.write ( "Please wait ...\n" )
#			)

			try:
				self._err_queue.push ( context=-1, error=None )

				while hasattr ( self, '_workers' ) and self._workers is not None:
					if True in ( w.active() for w in self._workers ):
						self._pkg_queue.put_nowait ( None )
					else:
						del self._workers
						self._workers = None
			finally:
#				signal.signal ( signal.SIGINT, SIGINT_RESTORE )
				raise

		finally:
			self._runlock.release()

		return start
	# --- end of _waitfor_workers (...) ---

	def _join_workers ( self ):
		"""Waits until all workers are done."""
		start = self._waitfor_workers ( False )
		if start is not None:
			self._timestamp ( "worker threads are done", start )
	# --- end of _join_workers (...) ---

	def _close_workers ( self ):
		"""Tells the workers to exit.
		This is done by disabling them and inserting empty requests (None as
		PackageInfo) to unblock them.
		"""
		start = self._waitfor_workers ( True )
		if start is not None:
			self._timestamp ( "worker threads are closed", start )
	# --- end of _close_workers (...) ---

	def _pkg_done ( self, package_info ):
		"""This is an event method used by worker threads when they have
		processed a package info.

		arguments:
		* package_info --
		"""
		if package_info ['ebuild'] is not None:
			self.create_success.inc()
			if package_info.overlay_package_ref.new_ebuild():
				self.overlay_added.inc()
		else:
			package_info.overlay_package_ref.ebuild_uncreateable ( package_info )
			self.create_fail.inc()

	# --- end of _add_to_overlay (...) ---

	def _get_worker ( self, start_now=False, use_threads=True ):
		"""Creates and returns a worker.

		arguments:
		* start_now   -- if set and True: start the worker immediately
		* use_threads -- if set and False: disable threads
		"""
		w = OverlayWorker (
			self._pkg_queue, self.depresolver, self.logger, self._pkg_done,
			use_threads=use_threads,
			err_queue=self._err_queue
		)
		if start_now: w.start()
		return w
	# --- end of _get_worker (...) ---

	def _make_workers ( self ):
		"""Creates and starts workers."""
		self._close_workers()

		if self.NUMTHREADS > 0:
			start = time.time()
			self.logger.warning (
				"Running in concurrent mode with {num} threads.".format (
					num=self.NUMTHREADS
			) )
			self._workers = frozenset (
				self._get_worker ( start_now=True ) \
					for n in range ( self.NUMTHREADS )
			)
			self._timestamp ( "worker threads initialized", start )
		else:
			self._workers = (
				self._get_worker ( start_now=True, use_threads=False ),
			)

	# --- end of _make_workers (...) ---
