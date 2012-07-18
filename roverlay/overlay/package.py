# R Overlay -- overlay module, package dir (subdir of category)
# Copyright 2006-2012 Gentoo Foundation
# Distributed under the terms of the GNU General Public License v2

import threading
import os
import sys

from roverlay                  import manifest
from roverlay.packageinfo      import PackageInfo
from roverlay.overlay.metadata import MetadataJob

SUPPRESS_EXCEPTIONS = True
EBUILD_SUFFIX = '.ebuild'

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
		# { <version> : <PackageInfo> }
		self._packages         = dict()
		self._metadata         = None
		self.physical_location = directory

		self._package_for_manifest = None

		# used to track changes for this package dir
		self.modified          = False
	# --- end of __init__ (...) ---

	def list_versions ( self ):
		return self._packages.keys()
	# --- end of list_versions (...) ---

	def has_manifest ( self ):
		return os.path.isfile (
			self.physical_location + os.sep + 'Manifest'
		)
	# --- end of has_manifest (...) ---

	def has_metadata ( self ):
		return os.path.isfile (
			self.physical_location + os.sep + 'metadata.xml'
		)
	# --- end of has_metadata (...) ---

	def get_ebuilds ( self ):
		for x in os.listdir ( self.physical_location ):
			if x.endswith ( EBUILD_SUFFIX ):
				yield self.physical_location + os.sep + x
	# --- end of get_ebuilds (...) ---

	def _scan_ebuilds ( self ):
		"""Searches for ebuilds in self.physical_location."""
		elen = len ( EBUILD_SUFFIX )

		for f in os.listdir ( self.physical_location ):
			if f.endswith ( EBUILD_SUFFIX ):
				try:
					# filename without suffix ~= ${PF} := ${PN}-${PVR}
					pn, pvr = f [ : - elen ].split ( '-', 1 )
					if pn == self.name:
						yield pvr
					else:
						# $PN does not match directory name, warn about that
						self.logger.warning (
							"$PN does not match directory name, ignoring {!r}.".\
							format ( f )
						)

				except:
					self.logger.warning (
						"ebuild {!r} has an invalid file name!".format ( f )
					)

	# --- end of _scan_ebuilds (...) ---

	def scan ( self, **kw ):
		"""Scans the filesystem location of this package for existing
		ebuilds and adds them.
		"""
		for pvr in self._scan_ebuilds():
			if pvr not in self._packages:
				p = PackageInfo ( physical_only=True, pvr=pvr )
				self._packages [ p ['ebuild_verstr'] ] = p
	# --- end of scan (...) ---

	def empty ( self ):
		"""Returns True if no ebuilds stored, else False."""
		return len ( self._packages ) == 0
	# --- end of empty (...) ---

	def _get_ebuild_filepath ( self, pvr ):
		"""Returns the path to the ebuild file.

		arguments:
		* pvr -- version number with the revision (${PVR} in ebuilds)
		"""
		return "{root}{sep}{PN}-{PVR}{EBUILD_SUFFIX}".format (
			root=self.physical_location, sep=os.sep,
			PN=self.name, PVR=pvr, EBUILD_SUFFIX=EBUILD_SUFFIX
		)
	# --- end of _get_ebuild_filepath (...) ---

	def write_incremental ( self, default_header ):
		self.write_ebuilds ( header=default_header, overwrite=False )
	# --- end of write_incremental (...) ---

	def write_metadata ( self, shared_fh=None ):
		"""Writes metadata for this package."""
		try:

			self._regen_metadata()

			if shared_fh is None:
				fh = open (
					self.physical_location + os.sep + self._metadata.filename, 'w'
				)
			else:
				fh = shared_fh

			self._metadata.write ( fh )

		except IOError as e:

			self.logger.error (
				"Failed to write metadata file {}.".format ( mfile )
			)
			self.logger.exception ( e )

		finally:
			if shared_fh is None and 'fh' in locals() and fh:
				fh.close()
	# --- end of write_metadata (...) ---

	def write_ebuild ( self, efile, ebuild, header, shared_fh=None ):
		"""Writes an ebuild.

		arguments:
		* efile     -- file to write
		* ebuild    -- ebuild object to write (has to have a __str__ method)
		* header    -- ebuild header to write (^)
		* shared_fh -- optional, see write_ebuilds()
		"""
		_success = False
		try:
			fh = open ( efile, 'w' ) if shared_fh is None else shared_fh
			if header is not None:
				fh.write ( str ( header ) )
				fh.write ( '\n\n' )
			fh.write ( str ( ebuild ) )
			fh.write ( '\n' )

			# adjust owner/perm? TODO
			#if shared_fh is None:
			#	chmod 0644 or 0444
			#	chown 250.250
			_success = True
		except IOError as e:
			self.logger.exception ( e )
		finally:
			if shared_fh is None and 'fh' in locals() and fh:
				fh.close()

		return _success
	# --- end of write_ebuild (...) ---

	def write_ebuilds ( self, header, shared_fh=None, overwrite=True ):
		"""Writes all ebuilds.

		arguments:
		* header    -- ebuild header
		* shared_fh -- if set and not None: don't use own file handles (i.e.
		               write files), write everything into shared_fh
		"""
		for ver, p_info in self._packages.items():
			if not p_info ['physical_only'] and p_info ['ebuild']:
				efile = self._get_ebuild_filepath ( ver )

				if not overwrite and efile == p_info ['ebuild_file']:
					print ( efile + " exists, skipping write()." )


				elif self.write_ebuild (
					efile, p_info ['ebuild'], header, shared_fh
				):
					if shared_fh is None:
						# this marks the package as 'written to fs'
						p_info.update_now (
							ebuild_file=efile,
							remove_auto='ebuild_written'
						)

						self._package_for_manifest = p_info

						self.logger.info ( "Wrote ebuild {}.".format ( efile ) )
				else:
					self.logger.error (
						"Couldn't write ebuild {}.".format ( efile )
					)
	# --- end of write_ebuilds (...) ---

	def write ( self,
		default_header=None, write_manifest=True, shared_fh=None
	):
		"""Writes this directory to its (existent!) filesystem location.

		arguments:
		* default_header    -- ebuild header to write
		* write_manifest -- if set and False: don't write the Manifest file

		returns: None (implicit)

		raises:
		* IOError
		"""
		self._lock.acquire()
		try:
			# mkdir not required here, overlay.Category does this

			# write ebuilds
			self.write_ebuilds ( header=default_header, shared_fh=shared_fh )

			# write metadata
			self.write_metadata ( shared_fh=shared_fh )

			if write_manifest and shared_fh is not None:
				self.write_manifest()

		finally:
			self._lock.release()
	# --- end of write (...) ---

	def show ( self, stream=sys.stderr, default_header=None ):
		"""Prints this dir (the ebuilds and the metadata) into a stream.

		arguments:
		* stream -- stream to use, defaults to sys.stderr

		returns: None (implicit)

		raises:
		* IOError
		"""
		self.write (
			default_header=default_header, shared_fh=stream, write_manifest=False
		)
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
		try:
			for p in self._packages.values():
				if pkg_filter is None or pkg_filter ( p ):
					newver = p ['version']
					if first or newver > retver:
						retver = newver
						retpkg = p
						first  = False
		finally:
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
		shortver = package_info ['ebuild_verstr']

		def already_exists ():
			if shortver in self._packages:
				self.logger.info (
					"'{PN}-{PVR}.ebuild' already exists, cannot add it!".format (
						PN=self.name, PVR=shortver
					)
				)
				return True
			else:
				return False
		# --- end of already_exists (...) ---

		_success = False

		if not already_exists():
			try:
				self._lock.acquire()
				if not already_exists():
					self._packages [shortver] = package_info
					self.modified = True
					_success = True
			finally:
				self._lock.release()

		return _success
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
		* use_all_packages -- TODO in metadata
		* use_old_metadata -- TODO in metadata
		"""
		if use_old_metadata or use_all_packages:
			raise Exception ( "using >1 package for metadata.xml is TODO!" )

		if skip_if_existent and not self._metadata is None: return

		self._lock.acquire()
		try:

			if self._metadata is None or not use_old_metadata:
				del self._metadata
				self._metadata = MetadataJob ( self.logger )

			if use_all_packages:
				for p_info in self._packages:
					self._metadata.update ( p_info )
			else:
				self._metadata.update ( self._latest_package() )

		finally:
			self._lock.release()
	# --- end of generate_metadata (...) ---

	def write_manifest ( self ):
		"""Generates and writes the Manifest file for this package.

		expects: called in self.write(), after writing metadata/ebuilds

		returns: None (implicit)

		raises:
		* Exception if no ebuild exists
		"""

		# it should be sufficient to call create_manifest for one ebuild,
		#  choosing the latest one here that exists in self.physical_location.
		#
		# metadata.xml's full path cannot be used for manifest creation here
		#  'cause DISTDIR would be unknown
		#
#		pkg_info_for_manifest = self._latest_package (
#			pkg_filter=lambda pkg : pkg ['ebuild_file'] is not None,
#			use_lock=True
#		)

		if self._package_for_manifest is None:
			# ? FIXME
			raise Exception (
				"No ebuild written so far! I really don't know what do to!"
			)
		else:
			# TODO: manifest creation interface is single threaded,
			#        may want to 'fix' this later
			manifest.create_manifest (
				self._package_for_manifest, nofail=False,
				#ebuild_file=...
			)

	# --- end of write_manifest (...) ---
