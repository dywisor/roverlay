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

class Category ( object ):

	WRITE_JOBCOUNT = 3

	def __init__ ( self, name, logger, directory, get_header, incremental ):
		"""Initializes a overlay/portage category (such as 'app-text', 'sci-R').

		arguments:
		* name       -- name of the category
		* logger     -- parent logger
		* directory  -- filesystem location
		* get_header -- function that returns an ebuild header
		"""
		self.logger            = logger.getChild ( name )
		self.name              = name
		self._lock             = threading.RLock()
		self._subdirs          = dict()
		self.physical_location = directory
		self.get_header        = get_header
		self.incremental       = incremental
	# --- end of __init__ (...) ---

	def _get_package_dir ( self, pkg_name ):
		if not pkg_name in self._subdirs:
			self._lock.acquire()
			try:
				if not pkg_name in self._subdirs:
					newpkg = PackageDir (
						name        = pkg_name,
						logger      = self.logger,
						directory   = self.physical_location + os.sep + pkg_name,
						get_header  = self.get_header,
						incremental = self.incremental
					)
					self._subdirs [pkg_name] = newpkg
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

	def empty ( self ):
		"""Returns True if this category contains 0 ebuilds."""
		return \
			len ( self._subdirs ) == 0 or \
			not False in ( d.empty() for d in self._subdirs.values() )
	# --- end of empty (...) ---

	def has ( self, subdir ):
		return subdir in self._subdirs
	# --- end of has (...) ---

	def has_dir ( self, _dir ):
		return os.path.isdir ( self.physical_location + os.sep + _dir )
	# --- end of has_category (...) ---

	def list_packages ( self, for_deprules=False ):
		"""Lists all packages in this category.
		Yields <category>/<package name> or a dict (see for_deprules below).

		arguments:
		* for_deprules -- if set and True:
		                   yield keyword args for dependency rules
		"""

		for name, subdir in self._subdirs.items():
			if not subdir.empty():
				if for_deprules:
					yield dict (
						dep_str=name, resolving_package=self.name + os.sep + name
					)
				else:
					yield self.name + os.sep + name
	# --- end of list_packages (...) ---

	def remove_empty ( self ):
		"""This removes all empty PackageDirs."""
		with self._lock:
			for key in tuple ( self._subdirs.keys() ):
				if self._subdirs [key].check_empty():
					del self._subdirs [key]
	# --- end of remove_empty (...) ---

	def scan ( self, **kw ):
		"""Scans this category for existing ebuilds."""
		for subdir in os.listdir ( self.physical_location ):
			if self.has_dir ( subdir ):
				self._get_package_dir ( subdir ).scan ( **kw )
	# --- end of scan (...) ---

	def show ( self, **show_kw ):
		"""Prints this category (its ebuild and metadata files).

		returns: None (implicit)
		"""
		for package in self._subdirs.values():
			package.show ( **show_kw )
	# --- end of show (...) ---

	def write ( self, overwrite_ebuilds, keep_n_ebuilds, cautious ):
		"""Writes this category to its filesystem location.

		returns: None (implicit)
		"""
		def run_write_queue ( q, write_kw ):
			"""Calls <package>.write for every <package> received from the queue.

			arguments:
			* q        -- queue
			* write_kw -- keywords for write(...)
			"""
			try:
				while not q.empty():
					try:
						pkg = q.get_nowait()
						# remove manifest writing from threaded writing since it's
						# single-threaded
						pkg.write ( write_manifest=False, **write_kw )
					#except ( Exception, KeyboardInterrupt ) as e:
					except Exception as e:
						# FIXME: reintroduce RERAISE
						self.logger.exception ( e )
			except queue.Empty:
				pass
		# --- end of run_write_queue (...) ---

		if len ( self._subdirs ) == 0: return

		# determine write keyword args
		write_kwargs = dict (
			overwrite_ebuilds = overwrite_ebuilds,
			keep_n_ebuilds    = keep_n_ebuilds,
			cautious          = cautious,
		)

		# start writing:

		max_jobs = self.__class__.WRITE_JOBCOUNT

		# FIXME/TODO: what's an reasonable number of min package dirs to
		# start threaded writing?
		# Ignoring it for now (and expecting enough pkg dirs)
		if max_jobs > 1:

			# writing <=max_jobs package dirs at once

			# don't create more workers than write jobs available
			max_jobs = min ( max_jobs, len ( self._subdirs ) )

			write_queue = queue.Queue()
			for package in self._subdirs.values():
				write_queue.put_nowait ( package )

			workers = frozenset (
				threading.Thread (
					target=run_write_queue,
					args=( write_queue, write_kwargs )
				) for n in range ( max_jobs )
			)

			for w in workers: w.start()
			for w in workers: w.join()

			self.remove_empty()

			# write manifest files
			# fixme: debug print
			#self.logger.info ( "Writing Manifest files for {}".format ( name ) )
			print ( "Writing Manifest files ..." )
			for package in self._subdirs.values():
				package.write_manifest ( ignore_empty=True )

		else:
			for package in self._subdirs.values():
				package.write ( **write_kwargs )

			self.remove_empty()
	# --- end of write (...) ---

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
