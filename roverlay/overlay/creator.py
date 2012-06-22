# R Overlay -- R package -> overlay interface
# Copyright 2006-2012 Gentoo Foundation
# Distributed under the terms of the GNU General Public License v2

import time
import logging
import threading

try:
	import queue
except ImportError:
	# python2
	import Queue as queue


from roverlay                    import config
from roverlay.overlay            import Overlay
from roverlay.overlay.worker     import OverlayWorker
from roverlay.packageinfo        import PackageInfo

from roverlay.recipe             import easyresolver

LOGGER = logging.getLogger ( 'OverlayCreator' )

OVERLAY_WRITE_ALLOWED = False


class OverlayCreator ( object ):
	"""This is a 'R packages -> Overlay' interface."""

	def __init__ ( self, logger=None ):

		if logger is None:
			self.logger = LOGGER
		else:
			self.logger = logger.getChild ( 'OverlayCreator' )

		# init overlay using config values
		self.overlay     = Overlay ( logger=self.logger )

		self.depresolver = easyresolver.setup()

		self.NUMTHREADS  = config.get ( 'EBUILD.jobcount', 0 )

		# --
		self._pkg_queue  = queue.Queue()
		self._workers    = None
		self._runlock    = threading.RLock()

		self.can_write_overlay = OVERLAY_WRITE_ALLOWED

	# --- end of __init__ (...) ---

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
			"timestamp: %s (after %f seconds)" % ( description, delta )
		)
		return _stop
	# --- end of _timestamp (...) ---

	def add ( self, *to_add ):
		"""Add a directory/package files/distdir to the package queue."""
		raise Exception ( "method stub" )
	# --- end of add (...) ---

	def add_package_file ( self, package_file ):
		"""Adds a single R package."""
		self._pkg_queue.put ( PackageInfo ( filepath=package_file ) )
	# --- end of add_package (...) ---

	def add_package_files ( self, *package_files ):
		"""Adds multiple R packages."""
		for p in package_files: self.add_package_file ( p )
	# --- end of add_packages (...) ---

	def add_directory ( self, directory ):
		"""Adds all packages from a directory to the package queue."""
		raise Exception ( "method stub" )
	# --- end of add_directory (...) ---

	def add_distdir ( self, repo_name ):
		"""Adds a distfiles directory to the package queue."""
		self.add_directory ( config.get_or_fail ( [ 'DISTFILES', repo_name ] ) )
	# --- end of add_distdir (...) ---

	def write_overlay ( self, incremental=False ):
		"""Writes the overlay.

		arguments:
		* incremental -- (TODO)
		"""
		if self.can_write_overlay:
			start = time.time()
			if incremental:
				# this will fail 'cause not implemented
				self.overlay.write_incremental()
			else:
				self.overlay.write()

			self._timestamp ( "overlay written", start )
		else:
			self.logger.warning ( "Not allowed to write overlay!" )
	# --- end of write_overlay (...) ---

	def show_overlay ( self ):
		"""Prints the overlay to the console. Does not create Manifest files."""
		self.overlay.show()
	# --- end of show_overlay (...) ---

	def run ( self ):
		"""Starts ebuild creation and waits until done."""
		self._runlock.acquire()
		self.start()
		self.join()
		self._runlock.release()
	# --- end of run (...) ---

	def start ( self ):
		"""Starts ebuild creation."""
		self._runlock.acquire()
		self.join()
		self._make_workers()
		self._runlock.release()
	# --- end of start (...) ---

	def join ( self ):
		"""Waits until ebuild creation is done."""
		self._join_workers()
	# --- end of wait (...) ---

	def close ( self, write=False ):
		"""Closes this OverlayCreator."""
		self._close_workers()
		self._close_resolver()
		if write: self.write_overlay()
	# --- end of close (...) ---

	def _close_resolver ( self ):
		"""Tells the dependency resolver to close.
		This is useful 'cause certain depres listener modules will write files
		when told to exit.
		"""
		if self.depresolver is None: return

		self._runlock.acquire()
		if self.depresolver is None: return

		self.depresolver.close()
		del self.depresolver
		self.depresolver = None

		self._runlock.release()
	# --- end of _close_resolver (...) ---

	def _waitfor_workers ( self, do_close ):
		"""Waits until the workers are done.

		arguments:
		* do_close -- close (exit) workers if True, else wait until done.
		"""
		if self._workers is None: return

		self._runlock.acquire()
		if self._workers is None: return

		if self.NUMTHREADS > 0: start = time.time()

		if do_close:
			for w in self._workers: w.enabled = False
		else:
			for w in self._workers: w.stop_when_empty()

		while True in ( w.active() for w in self._workers ):
			self._pkg_queue.put ( None )

		del self._workers
		self._workers = None

		self._runlock.release()
		if self.NUMTHREADS > 0: return start
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
		# ... TODO
		#  * increase the number of successful/failed packages,
		#  * request an incremental write to save memory etc.

		# if <>:
		if package_info ['ebuild'] is not None:
			self.overlay.add ( package_info )
	# --- end of _add_to_overlay (...) ---

	def _get_worker ( self, start_now=False, use_threads=True ):
		"""Creates and returns a worker.

		arguments:
		* start_now   -- if set and True: start the worker immediately
		* use_threads -- if set and False: disable threads
		"""
		w = OverlayWorker (
			self._pkg_queue, self.depresolver, self.logger, self._pkg_done,
			use_threads=use_threads
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
				"Running in concurrent mode with %i threads." % self.NUMTHREADS
			)
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
