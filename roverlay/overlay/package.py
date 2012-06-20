# R Overlay -- <comment TODO>
# Copyright 2006-2012 Gentoo Foundation
# Distributed under the terms of the GNU General Public License v2

import threading
import os.path
import sys

from roverlay.metadata import MetadataJob
from roverlay          import manifest

SUPPRESS_EXCEPTIONS = True

class PackageDir ( object ):

	def __init__ ( self, name, logger, directory ):
		"""Initializes a PackageDir which contains ebuilds, metadata and
		a Manifest file.

		arguments:
		* name      -- name of the directory (${PN} in ebuilds)
		* logger    -- parent logger
		* directory -- filesystem location of this PackageDir
		"""
		self.logger            = logger.getChild ( name )
		self.name              = name
		self._lock             = threading.RLock()
		self._packages         = dict()
		self._metadata         = None
		self.physical_location = directory
	# --- end of __init__ (...) ---

	def empty ( self ):
		"""Returns True if no ebuilds stored, else False."""
		return len ( self._packages ) == 0
	# --- end of empty (...) ---

	def _get_metadata_filepath ( self ):
		"""Returns the path to the metadata file."""
		return os.path.join (
			'??' if self.physical_location is None else self.physical_location,
			self._metadata.filename
		)
	# --- end of _get_metadata_filepath (...) ---

	def _get_ebuild_filepath ( self, pvr ):
		"""Returns the path to the ebuild file.

		arguments:
		* pvr -- version number with the revision (${PVR} in ebuilds)
		"""
		filename = "%s-%s.ebuild" % ( self.name, pvr )
		return os.path.join (
			'??' if self.physical_location is None else self.physical_location,
			filename
		)
	# --- end of _get_ebuild_filepath (...) ---

	def write ( self, default_header=None ):
		"""Writes this directory to its (existent!) filesystem location.

		returns: None (implicit)

		raises: !! TODO
		"""
		if self.physical_location is None:
			raise Exception ( "cannot write - no directory assigned!" )

		self._lock.acquire()
		self._regen_metadata()

		# mkdir not required here, overlay.Category does this

		# write ebuilds
		for ver, p_info in self._packages.items():
			fh = None
			try:
				efile  = self._get_ebuild_filepath ( ver )

				ebuild = p_info ['ebuild']

				fh = open ( efile, 'w' )
				if isinstance ( ebuild, str ):
					if default_header is not None:
						fh.write ( default_header )
						fh.write ( '\n\n' )
					fh.write ( ebuild )
					fh.write ( '\n' )
				else:
					ebuild.write (
						fh,
						header=default_header, header_is_fallback=True
					)
				if fh: fh.close()

				# adjust owner/perm? TODO
				# chmod 0644 or 0444
				# chown 250.250

				# this marks the package as 'written to fs'
				# TODO update PackageInfo
				p_info.set_writeable()
				p_info ['ebuild_file'] = efile
				p_info.set_readonly()

				self.logger.info ( "Wrote ebuild %s." % efile )
			except IOError as e:
				if fh: fh.close()
				self.logger.error ( "Couldn't write ebuild %s." % efile )
				self.logger.exception ( e )

		# write metadata
		fh = None
		try:
			mfile = self._get_metadata_filepath()

			fh    = open ( mfile, 'w' )
			self._metadata.write ( fh )
			if fh: fh.close()

		except IOError as e:
			if fh: fh.close()
			self.logger.error ( "Failed to write metadata at %s." % mfile )
			self.logger.exception ( e )

		self.generate_manifest()

		self._lock.release()
	# --- end of write (...) ---

	def show ( self, stream=sys.stderr, default_header=None ):
		"""Prints this dir (the ebuilds and the metadata) into a stream.

		arguments:
		* stream -- stream to use, defaults to sys.stderr

		returns: None (implicit)

		raises: !! TODO
		"""
		self._lock.acquire()
		self._regen_metadata()


		for ver, p_info in self._packages.items():
			efile  = self._get_ebuild_filepath ( ver )
			ebuild = p_info ['ebuild']

			stream.write ( "[BEGIN ebuild %s]\n" % efile )
			ebuild.write (
				stream,
				header=default_header, header_is_fallback=True
			)
			stream.write ( "[END ebuild %s]\n" % efile )

		mfile = self._get_metadata_filepath()

		stream.write ( "[BEGIN %s]\n" % mfile )
		self._metadata.write ( stream )
		stream.write ( "[END %s]\n" % mfile )


		self._lock.release()
	# --- end of show (...) ---

	def _latest_package ( self, pkg_filter=None, use_lock=False ):
		"""Returns the package info with the highest version number.

		arguments:
		* pkg_filter -- either None or a callable,
		                 None: do not filter packages
		                 else: ignore package if it does not pass the filter
		* use_lock   -- if True: hold lock while searching
		"""
		first  = True
		retver = None
		retpkg = None

		if use_lock: self._lock.acquire()
		for p in self._packages.values():
			if pkg_filter is None or pkg_filter ( p ):
				newver = p ['version']
				if first or newver > retver:
					retver = newver
					retpkg = p
					first  = False

		if use_lock: self._lock.release()
		return retpkg
	# --- end of _latest_package (...) ---

	def add ( self, package_info ):
		"""Adds a package to this PackageDir.

		arguments:
		* package_info --

		returns: success as bool

		raises: Exception when ebuild already exists.
		"""
		# !! p info key TODO
		shortver = package_info ['ebuild_verstr']

		def already_exists ( release=False ):
			if shortver in self._packages:

				if release: self._lock.release()

				msg = "'%s-%s.ebuild' already exists, cannot add it!" % (
					self.name, shortver
				)
				if SUPPRESS_EXCEPTIONS:
					logger.warning ( msg )
				else:
					raise Exception ( msg )

				return True
			else:
				return False
		# --- end of already_exists (...) ---

		if already_exists ( release=False ): return False
		self._lock.acquire()
		if already_exists ( release=True  ): return False

		self._packages [shortver] = package_info

		self._lock.release()
		return True
	# --- end of add (...) ---

	def _regen_metadata ( self ):
		"""Regenerates the metadata."""
		self.generate_metadata (
			skip_if_existent=True,
			use_all_packages=False,
			use_old_metadata=False
		)
	# --- end of _regen_metadata (...) ---

	def generate_metadata (
		self,
		skip_if_existent=False, use_all_packages=False, use_old_metadata=False
	):
		"""Creates metadata for this package.

		arguments:
		* skip_if_existent -- do not create if metadata already exist
		* use_all_packages -- TODO
		* use_old_metadata -- TODO
		"""
		if use_old_metadata or use_all_packages:
				raise Exception ( "using >1 package for metadata.xml is TODO!" )

		if skip_if_existent and not self._metadata is None:
			return

		self._lock.acquire()

		if self._metadata is None or not use_old_metadata:
			del self._metadata
			self._metadata = MetadataJob ( self.logger )

		if use_all_packages:
			for p_info in self._packages:
				self._metadata.update ( p_info )
		else:
			self._metadata.update ( self._latest_package() )

		self._lock.release()
	# --- end of generate_metadata (...) ---

	def generate_manifest ( self ):
		"""Generates the Manifest file for this package.

		expects: called in self.write(), after writing metadata/ebuilds

		returns: None (implicit)

		raises: !! TODO
		* Exception if not physical
		"""
		if self.physical_location is None:
			raise Exception ( "no directory assigned." )

		# it should be sufficient to call create_manifest for one ebuild,
		#  choosing the latest one here that exists in self.physical_location.
		#
		# metadata.xml's full path cannot be used for manifest creation here
		#  'cause DISTDIR would be unknown
		#
		pkg_info_for_manifest = self._latest_package (
			pkg_filter=lambda pkg : not pkg ['ebuild_file'] is None,
			use_lock=True
		)

		if pkg_info_for_manifest is None:
			# ? FIXME
			raise Exception (
				"No ebuild written so far! I really don't know what do to!"
			)
		else:
			# TODO: manifest creation interface is single threaded,
			#        may want to 'fix' this later
			manifest.create_manifest ( pkg_info_for_manifest, nofail=False )

	# --- end of generate_manifest (...) ---
