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

	def has ( self, subdir ):
		return subdir in self._subdirs
	# --- end of has (...) ---

	def list_packages ( self, print_category=True ):
		if print_category:
			for package in self._subdirs.keys():
				yield self.name + os.sep + package
		else:
			for package in self._subdirs.keys():
				yield package
	# --- end of list_packages (...) ---

	def has_dir ( self, _dir ):
		return os.path.isdir ( self.physical_location + os.sep + _dir )
	# --- end of has_category (...) ---

	def _scan_packages ( self ):
		for x in os.listdir ( self.physical_location ):
			if self.has_dir ( x ):
				yield self._get_package_dir ( x )
	# --- end of _scan_packages (...) ---

	def scan ( self, **kw ):
		for pkg in self._scan_packages():
			pkg.scan ( **kw )
	# --- end of scan (...) ---

	def empty ( self ):
		"""Returns True if this category contains 0 ebuilds."""
		return \
			len ( self._subdirs ) == 0 or \
			not False in ( d.empty() for d in self._subdirs.values() )
	# --- end of empty (...) ---

	def finalize_write_incremental ( self ):
		for subdir in self._subdirs.values():
			if subdir.modified:
				subdir.write_incremental()
			subdir.finalize_write_incremental()
	# --- end of finalize_write_incremental (...) ---

	def _get_package_dir ( self, pkg_name ):
		if not pkg_name in self._subdirs:
			self._lock.acquire()
			try:
				if not pkg_name in self._subdirs:
					self._subdirs [pkg_name] = PackageDir (
						pkg_name,
						self.logger,
						self.physical_location + os.sep + pkg_name
					)
			finally:
				self._lock.release()

		return self._subdirs [pkg_name]
	# --- end of _get_package_dir (...) ---

	def add ( self, package_info, **pkg_add_kw ):
		"""Adds a package to this category.

		arguments:
		* package_info --

		returns: success
		"""
		subdir = self._get_package_dir ( package_info ['name'] )
		return subdir.add ( package_info, **pkg_add_kw )
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

	def write_manifest ( self, **manifest_kw ):
		"""Generates Manifest files for all packages in this category.
		Manifest files are automatically created when calling write().

		arguments:
		* **manifest_kw -- see PackageDir.write_manifest(...)

		returns: None (implicit)
		"""
		for package in self._subdirs.values():
			package.write_manifest ( **manifest_kw )
	# --- end of write_manifest (...) ---

	def show ( self, **show_kw ):
		"""Prints this category (its ebuild and metadata files).

		returns: None (implicit)
		"""
		for package in self._subdirs.values():
			package.show ( **show_kw )
	# --- end of show (...) ---

	def _run_write_queue ( self, q, write_kw ):
		"""Calls <package>.write for every <package> received from the queue.

		arguments:
		* q        -- queue
		* write_kw --
		"""
		try:
			while not q.empty():
				pkg = q.get_nowait()
				pkg.write ( write_manifest=False, **write_kw )

		except queue.Empty:
			pass
		except ( Exception, KeyboardInterrupt ) as e:
			self.RERAISE_EXCEPTION = e

	# --- end of _run_write_queue (...) ---

	def write_incremental ( self, **write_kw ):
		"""Writes this category incrementally."""
		try:
			with self._lock:
				# new package dirs could be added during overlay writing,
				# so collect the list of package dirs before iterating over it
				subdirs = tuple ( self._subdirs.values() )

			for subdir in subdirs:
				if subdir.modified:
					roverlay.util.dodir ( subdir.physical_location )
					subdir.write_incremental ( **write_kw )
		except Exception as e:
			self.logger.exception ( e )
	# --- end of write_incremental (...) ---

	def write ( self, **write_kw ):
		"""Writes this category to its filesystem location.

		returns: None (implicit)
		"""

		max_jobs = self.__class__.WRITE_JOBCOUNT

		# todo len.. > 3: what's an reasonable number of min package dirs to
		#                  start threaded writing?
		if max_jobs > 1 and len ( self._subdirs ) > 3:

			# writing 1..self.__class__.WRITE_JOBCOUNT package dirs at once

			modified_packages = tuple (
				p for p in self._subdirs.values() if p.modified
			)
			if len ( modified_packages ) > 0:
				write_queue = queue.Queue()
				for package in modified_packages:
					roverlay.util.dodir ( package.physical_location )
					write_queue.put_nowait ( package )

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

				# write manifest files
				for package in modified_packages:
					package.write_manifest()

		else:
			for package in self._subdirs.values():
				if package.modified:
					roverlay.util.dodir ( package.physical_location )
					package.write ( write_manifest=True, **write_kw )
	# --- end of write (...) ---
