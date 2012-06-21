
import time
import threading

try:
	import queue
except ImportError:
	# python2
	import Queue as queue


from roverlay.depres.channels    import EbuildJobChannel
from roverlay.ebuild.creation    import EbuildCreation

class OverlayWorker ( object ):

	def __init__ ( self, pkg_queue, depresolver, logger, pkg_done, use_threads ):
		self.logger      = logger
		self.pkg_queue   = pkg_queue
		self.pkg_done    = pkg_done
		self.depresolver = depresolver


		self.enabled     = True
		self.running     = False
		self._use_thread = use_threads
		self._thread     = None

	# --- end of __init__ (...) ---

	def start ( self ):
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

	def active ( self ):
		return self.running or self.enabled
	# --- end of active (...) ---

	def _get_resolver_channel ( self, **channel_kw ):
		return self.depresolver.register_channel (
			EbuildJobChannel ( **channel_kw )
		)
	# --- end of _get_resolver_channel (...) ---

	def _process ( self, package_info ):
		job = EbuildCreation (
			package_info,
			depres_channel_spawner=self._get_resolver_channel
		)
		job.run()
		self.pkg_done ( package_info )
	# --- end of _process (...) ---

	def _run ( self ):
		self.running = True
		while self.enabled:
			p = self.pkg_queue.get()

			# drop empty requests that are used to unblock get()
			if p is not None:
				self._process ( p )

			self.pkg_queue.task_done()
		self.running = False
	# --- end of run (...) ---

	def _run_nothread ( self ):
		self.running = True
		while self.enabled and not self.pkg_queue.empty():
			p = self.pkg_queue.get()

			# drop empty requests that are used to unblock get()
			if p is not None:
				self._process ( p )

			self.pkg_queue.task_done()
		self.running = False
	# --- end of _run_nothread (...) ---
