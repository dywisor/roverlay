# R Overlay -- overlay module, portage category
# Copyright 2006-2012 Gentoo Foundation
# Distributed under the terms of the GNU General Public License v2

import threading
import os.path

from roverlay.overlay.package import PackageDir

import roverlay.util

class Category ( object ):

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

	def empty ( self ):
		"""Returns True if this category contains 0 ebuilds."""
		return \
			len ( self._subdirs ) == 0 or \
			not False in ( d.empty() for d in self._subdirs.values() )
	# --- end of empty (...) ---

	def add ( self, package_info ):
		"""Adds a package to this category.

		arguments:
		* package_info --

		returns: None (implicit)
		"""
		pkg_name = package_info ['name']

		if not pkg_name in self._subdirs:
			self._lock.acquire()
			if not pkg_name in self._subdirs:
				self._subdirs [pkg_name] = PackageDir (
					pkg_name,
					self.logger,
					None if self.physical_location is None else \
						os.path.join ( self.physical_location, pkg_name )
				)
			self._lock.release()

		self._subdirs [pkg_name].add ( package_info )
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

	def write ( self, **write_kw ):
		"""Writes this category to its filesystem location.

		returns: None (implicit)
		"""
		for package in self._subdirs.values():
			if package.physical_location and not package.empty():
				roverlay.util.dodir ( package.physical_location )
				package.write ( **write_kw )
	# --- end of write (...) ---
