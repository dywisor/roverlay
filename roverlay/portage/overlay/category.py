# R Overlay -- <comment TODO>
# Copyright 2006-2012 Gentoo Foundation
# Distributed under the terms of the GNU General Public License v2

import threading
import os.path


from roverlay.portage.overlay.package import PackageDir

import roverlay.util

class Category ( object ):

	def __init__ ( self, name, logger, directory ):
		self.logger            = logger.getChild ( name )
		self.name              = name
		self._lock             = threading.RLock()
		self._subdirs          = dict()
		self.physical_location = directory
	# --- end of __init__ (...) ---

	def empty ( self ):
		return \
			len ( self._subdirs ) == 0 or \
			not False in ( d.empty() for d in self._subdirs )
	# --- end of empty (...) ---

	def set_fs_location ( self, directory ):
		self._lock.acquire()
		self.physical_location = directory

		if not directory is None:
			for pkg_name, pkg in self._subdirs.items():
				pkg.set_fs_location (
					os.path.join ( directory, pkg_name )
				)

		self._lock.release()
	# --- end of set_fs_location (...) ---

	def add ( self, package_info ):
		# TODO make keys available
		pkg_name = package_info ['name']

		if not pkg_name in self._content:
			self._lock.acquire()
			if not pkg_name in self._content:
				self._content [pkg_name] = PackageDir (
					pkg_name,
					self.logger,
					None if self.physical_location is None else \
						os.path.join ( self.physical_location, pkg_name )
				)
			self._lock.release()

		self._content [pkg_name].add ( package_info )
	# --- end of add (...) ---

	def generate_metadata ( self, **metadata_kw ):
		for package in self._subdirs.values():
			package.generate_metadata ( **metadata_kw )
	# --- end of generate_metadata (...) ---

	def show ( self, **show_kw ):
		for package in self._subdirs.values():
			package.show ( **show_kw )
	# --- end of show (...) ---

	def write ( self ):
		for package in self._subdirs.values():
			if package.physical_location and not package.empty():
				roverlay.util.dodir ( package.physical_location )
				package.write()

	# --- end of write (...) ---

	def ls ( self ):
		return frozenset (
			( os.path.join ( n, p.ls() ) for n, p in self._subdirs.items() )
		)

	def __str__ ( self ): return '\n'.join ( self.ls() )


