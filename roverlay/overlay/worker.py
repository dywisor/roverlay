# R Overlay -- R package -> overlay interface, PackageInfo worker
# Copyright 2006-2012 Gentoo Foundation
# Distributed under the terms of the GNU General Public License v2

#import time
import sys
import threading

from roverlay.depres.channels    import EbuildJobChannel
from roverlay.ebuild.creation    import EbuildCreation

# this controls whether debug message from OverlayWorker.run() are printed
# to stderr or suppressed
DEBUG = True

class OverlayWorker ( object ):
	"""Overlay package queue worker."""

	def __init__ ( self,
		pkg_queue, depresolver, logger, pkg_done, use_threads, err_queue
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

		self.err_queue   = err_queue

		self._use_thread = use_threads
		self._thread     = None
		self.running     = False
		self.enabled     = True
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
			depres_channel_spawner=self._get_resolver_channel,
			err_queue=self.err_queue
		)
		job.run()
		self.pkg_done ( package_info )
	# --- end of _process (...) ---

	def _run ( self ):
		"""Runs the worker (thread mode)."""

		def debug ( msg ):
			if DEBUG:
				sys.stderr.write (
					"%i WORKER: %s\n" % ( id ( self ), msg )
				)

		try:
			self.running = True
			self.halting = False
			while self.enabled or (
				self.halting and not self.pkg_queue.empty()
			):
				if not self.err_queue.empty():
					# other workers died (or exit request sent)
					debug ( "STOPPING #1" )
					break

				debug ( "WAITING" )
				p = self.pkg_queue.get()
				debug ( "RECEIVED A TASK, " + str ( p ) )

				if not self.err_queue.empty():
					debug ( "STOPPING #2" )
					break

				# drop empty requests that are used to unblock get()
				if p is not None:
					debug ( "ENTER PROC" )
					if self.err_queue.empty():
						debug ( "__ empty exception/error queue!" )
					self._process ( p )
				elif self.halting:
					# receiving an empty request while halting means 'stop now',
					self.enabled = False
					self.halting = False

				self.pkg_queue.task_done()

			debug ( "STOPPING - DONE" )
		except ( Exception, KeyboardInterrupt ) as e:
			self.logger.exception ( e )
			self.err_queue.put_nowait ( ( id ( self ), e ) )

		self.running = False

	# --- end of run (...) ---

	def _run_nothread ( self ):
		"""Runs the worker (no-thread mode)."""
		self.running = True
		while self.enabled and not self.pkg_queue.empty():

			p = self.pkg_queue.get_nowait()

			# drop empty requests that are used to unblock get()
			if p is not None:
				self._process ( p )

			self.pkg_queue.task_done()

		self.running = False
	# --- end of _run_nothread (...) ---
