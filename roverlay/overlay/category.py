# R Overlay -- overlay module, portage category
# Copyright 2006-2012 Gentoo Foundation
# Distributed under the terms of the GNU General Public License v2

import threading
import os

try:
	import queue
except ImportError:
	import Queue as queue

from roverlay.overlay.package import PackageDir

import roverlay.util

class Category ( object ):

	WRITE_JOBCOUNT = 3

	def __init__ ( self, name, logger, directory ):
		"""Initializes a overlay/portage category (such as 'app-text', 'sci-R').

		arguments:
		* name      -- name of the category
		* logger    -- parent logger
		* directory -- filesystem location
		"""
		self.logger            = logger.getChild ( name )
		self.name              = name
		self._lock             = threading.RLock()
		self._subdirs          = dict()
		self.physical_location = directory
	# --- end of __init__ (...) ---

	def has_dir ( self, _dir ):
		return os.path.isdir ( self.physical_location + os.sep + _dir )
	# --- end of has_category (...) ---

	def _scan_packages ( self ):
		for x in os.listdir ( self.physical_location ):
			if self.has_dir ( x ):
				yield self._get_package_dir ( x )
	# --- end of _scan_packages (...) ---

	def scan ( self ):
		for pkg in self._scan_packages():
			print ( pkg.name )
			pkg.scan()
	# --- end of scan (...) ---

	def empty ( self ):
		"""Returns True if this category contains 0 ebuilds."""
		return \
			len ( self._subdirs ) == 0 or \
			not False in ( d.empty() for d in self._subdirs.values() )
	# --- end of empty (...) ---

	def _get_package_dir ( self, pkg_name ):
		if not pkg_name in self._subdirs:
			self._lock.acquire()
			try:
				if not pkg_name in self._subdirs:
					self._subdirs [pkg_name] = PackageDir (
						pkg_name,
						self.logger,
						None if self.physical_location is None else \
							os.path.join ( self.physical_location, pkg_name )
					)
			finally:
				self._lock.release()

		return self._subdirs [pkg_name]
	# --- end of _get_package_dir (...) ---

	def add ( self, package_info ):
		"""Adds a package to this category.

		arguments:
		* package_info --

		returns: success
		"""
		return self._get_package_dir (
			package_info ['name']
		).add ( package_info )
	# --- end of add (...) ---

	def generate_metadata ( self, **metadata_kw ):
		"""Generates metadata for all packages in this category.
		Metadata are automatically generated when calling write().

		arguments:
		* **metadata_kw -- see PackageDir.generate_metadata(...)

		returns: None (implicit)
		"""
		for package in self._subdirs.values():
			package.generate_metadata ( **metadata_kw )
	# --- end of generate_metadata (...) ---

	def generate_manifest ( self, **manifest_kw ):
		"""Generates Manifest files for all packages in this category.
		Manifest files are automatically created when calling write().

		arguments:
		* **manifest_kw -- see PackageDir.generate_manifest(...)

		returns: None (implicit)
		"""
		for package in self._subdirs.values():
			package.generate_manifest ( **manifest_kw )
	# --- end of generate_manifest (...) ---

	def show ( self, **show_kw ):
		"""Prints this category (its ebuild and metadata files).

		returns: None (implicit)
		"""
		for package in self._subdirs.values():
			package.show ( **show_kw )
	# --- end of show (...) ---

	def _run_write_queue ( self, q, write_kw ):
		try:
			while not q.empty():
				pkg = q.get_nowait()
				pkg.write ( **write_kw )

		except queue.Empty:
			pass
		except ( Exception, KeyboardInterrupt ) as e:
			self.RERAISE_EXCEPTION = e

	# --- end of _run_write_queue (...) ---

	def write ( self, **write_kw ):
		"""Writes this category to its filesystem location.

		returns: None (implicit)
		"""

		max_jobs = self.__class__.WRITE_JOBCOUNT

		# todo len.. > 3: what's an reasonable number of min package dirs to
		#                  start threaded writing?
		if max_jobs > 1 and len ( self._subdirs ) > 3:

			# writing 1..self.__class__.WRITE_JOBCOUNT package dirs at once

			write_queue = queue.Queue()
			for package in self._subdirs.values():
				if package.physical_location and not package.empty():
					roverlay.util.dodir ( package.physical_location )
					write_queue.put_nowait ( package )


			if not write_queue.empty():
				workers = (
					threading.Thread (
						target=self._run_write_queue,
						args=( write_queue, write_kw )
					) for n in range ( max_jobs )
				)

				for w in workers: w.start()
				for w in workers: w.join()

				if hasattr ( self, 'RERAISE_EXCEPTION' ):
					raise self.RERAISE_EXCEPTION
		else:
			for package in self._subdirs.values():
				if package.physical_location and not package.empty():
					roverlay.util.dodir ( package.physical_location )
					package.write ( **write_kw )
	# --- end of write (...) ---
