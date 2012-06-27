# R Overlay -- R package -> overlay interface, PackageInfo worker
# Copyright 2006-2012 Gentoo Foundation
# Distributed under the terms of the GNU General Public License v2

#import time
import threading

from roverlay.depres.channels    import EbuildJobChannel
from roverlay.ebuild.creation    import EbuildCreation

class OverlayWorker ( object ):
	"""Overlay package queue worker."""

	def __init__ ( self,
		pkg_queue, depresolver, logger, pkg_done, use_threads
	):
		"""Initializes a worker.

		arguments:
		* pkg_queue   -- queue with PackageInfos
		* depresolver -- dependency resolver to use
		* logger      -- logger to use
		* pkg_done    -- method to call when a PackageInfo has been
		                 processed
		* use_threads -- whether to run this worker as a thread or not
		"""
		self.logger      = logger
		self.pkg_queue   = pkg_queue
		self.pkg_done    = pkg_done
		self.depresolver = depresolver

		self._use_thread = use_threads
		self._thread     = None

		self.enabled     = True
		self.running     = False
		self.halting     = False
	# --- end of __init__ (...) ---

	def start ( self ):
		"""Starts the worker."""
		if self._thread is not None:
			self._thread.join()
			del self._thread

		self.enabled = True
		if self._use_thread:
			self._thread = threading.Thread ( target=self._run )
			self._thread.start()
		else:
			self._run_nothread()
	# --- end of start (...) ---

	def stop_when_empty ( self ):
		"""Tells the worker thread to exit when the queue is empty."""
		self.enabled = False
		self.halting = True
	# --- end of stop_when_empty (...) ---

	def active ( self ):
		"""Returns True if this worker is active (running or enabled)."""
		return self.running or self.enabled
	# --- end of active (...) ---

	def _get_resolver_channel ( self, **channel_kw ):
		"""Returns a resolver channel.

		arguments:
		* **channel_kw -- keywords for EbuildJobChannel.__init__
		"""
		return self.depresolver.register_channel (
			EbuildJobChannel ( **channel_kw )
		)
	# --- end of _get_resolver_channel (...) ---

	def _process ( self, package_info ):
		"""Processes a PackageInfo taken from the queue.

		arguments:
		* package_info --
		"""
		job = EbuildCreation (
			package_info,
			depres_channel_spawner=self._get_resolver_channel
		)
		job.run()
		self.pkg_done ( package_info )
	# --- end of _process (...) ---

	def _run ( self ):
		"""Runs the worker (thread mode)."""
		self.running = True
		self.halting = False
		while self.enabled or (
			self.halting and not self.pkg_queue.empty()
		):
			if not self.running:
				# exit now
				break
			p = self.pkg_queue.get()

			# drop empty requests that are used to unblock get()
			if p is not None:
				self._process ( p )
			elif self.halting:
				# receiving an empty request while halting means 'stop now',
				self.enabled = False
				self.halting = False

			self.pkg_queue.task_done()
		self.running = False
	# --- end of run (...) ---

	def _run_nothread ( self ):
		"""Runs the worker (no-thread mode)."""
		self.running = True
		while self.enabled and not self.pkg_queue.empty():
			if not self.running:
				# exit now
				break

			p = self.pkg_queue.get()

			# drop empty requests that are used to unblock get()
			if p is not None:
				self._process ( p )

			self.pkg_queue.task_done()
		self.running = False
	# --- end of _run_nothread (...) ---