import os
import sys
import threading

from roverlay.overlay          import manifest
from roverlay.packageinfo      import PackageInfo
from roverlay.overlay.metadata import MetadataJob

SUPPRESS_EXCEPTIONS = True


class PackageDir ( object ):
	EBUILD_SUFFIX = '.ebuild'

	def __init__ ( self, name, logger, directory, get_header, incremental ):
		"""Initializes a PackageDir which contains ebuilds, metadata and
		a Manifest file.

		arguments:
		* name       -- name of the directory (${PN} in ebuilds)
		* logger     -- parent logger
		* directory  -- filesystem location of this PackageDir
		* get_header -- function that returns an ebuild header
		"""
		self.logger              = logger.getChild ( name )
		self.name                = name
		self._lock               = threading.RLock()
		# { <version> : <PackageInfo> }
		self._packages           = dict()
		self.physical_location   = directory
		self.get_header          = get_header
		self.runtime_incremental = incremental

		self._metadata = MetadataJob (
			filepath = self.physical_location + os.sep + 'metadata.xml',
			logger   = self.logger
		)

		# <dir>/<PN>-<PVR>.ebuild
		self.ebuild_filepath_format = \
			self.physical_location + os.sep + \
			self.name + "-{PVR}" + self.__class__.EBUILD_SUFFIX

		# used to track changes for this package dir
		self.modified          = False
		self._manifest_package = None
		self._need_manifest    = False
		self._need_metadata    = False
	# --- end of __init__ (...) ---

	def add ( self, package_info, add_if_physical=False ):
		"""Adds a package to this PackageDir.

		arguments:
		* package_info    --
		* add_if_physical -- add package even if it exists as ebuild file
		                      (-> overwrite old ebuilds)

		returns: success as bool

		raises: Exception when ebuild already exists.
		"""
		shortver = package_info ['ebuild_verstr']
		added = False
		try:
			self._lock.acquire()
			if shortver in self._packages:
				# package exists, check if it existed before script invocation
				if self._packages [shortver] ['physical_only']:
					if add_if_physical:
						# else ignore ebuilds that exist as file
						self._packages [shortver] = package_info
						added = True

					else:
						self.logger.debug (
							"'{PN}-{PVR}.ebuild' exists as file, skipping.".format (
								PN=self.name, PVR=shortver
							)
						)
				else:
					# package has been added to this overlay before
					self.logger.info (
						"'{PN}-{PVR}.ebuild' already exists, cannot add it!".format (
						PN=self.name, PVR=shortver
						)
					)
			else:
				self._packages [shortver] = package_info
				added = True

		finally:
			self._lock.release()

		if added:
			# add a link to this PackageDir into the package info,
			# !! package_info <-> self (double-linked)
			# FIXME: remove physical_only flag from PackageInfo if
			#         overlay_package_ref can be used for that
			package_info.overlay_package_ref = self
			return True
		else:
			return False
	# --- end of add (...) ---

	def empty ( self ):
		"""Returns True if no ebuilds stored, else False.
		Note that "not empty" does not mean "have ebuilds to write".
		"""
		return len ( self._packages ) == 0
	# --- end of empty (...) ---

	def finalize_write_incremental ( self ):
		with self._lock:
			if self._need_metadata:
				self.write_metadata()
			if self._need_manifest:
				self.write_manifest()
	# --- end of finalize_write_incremental (...) ---

	def generate_metadata ( self, skip_if_existent, **ignored_kw ):
		"""Creates metadata for this package.

		arguments:
		* skip_if_existent -- do not create if metadata already exist
		"""
		with self._lock:
			if self._metadata.empty() or not skip_if_existent:
				self._metadata.update_using_iterable ( self._packages.values() )
	# --- end of generate_metadata (...) ---

	def list_versions ( self ):
		return self._packages.keys()
	# --- end of list_versions (...) ---

	def new_ebuild ( self, write=False ):
		"""Called when a new ebuild has been created for this PackageDir."""
		self._need_manifest = True
		self._need_metadata = True
		self.modified       = True
		if self.runtime_incremental:
			return self.write_incremental()
		else:
			return True
	# --- end of new_ebuild (...) ---

	def scan ( self, **kw ):
		"""Scans the filesystem location of this package for existing
		ebuilds and adds them.
		"""
		def scan_ebuilds():
			"""Searches for ebuilds in self.physical_location."""
			elen = len ( self.__class__.EBUILD_SUFFIX )
			def ebuild_split_pvr ( _file ):
				if _file.endswith ( self.__class__.EBUILD_SUFFIX ):
					return _file [ : - elen ].split ( '-', 1 )
				else:
					return ( None, None )
			# --- end of is_ebuild (...) ---

			# assuming that self.physical_location exists
			#  (should be verified by category.py:Category)
			for f in os.listdir ( self.physical_location ):
				try:
					# filename without suffix ~= ${PF} := ${PN}-${PVR}
					pn, pvr = ebuild_split_pvr ( f )
					if pn is None:
						# not an ebuild
						pass
					elif pn == self.name:
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
		# --- end of scan_ebuilds (...) ---

		# ignore directories without a Manifest file
		if os.path.isfile ( self.physical_location + os.sep + 'Manifest' ):
			for pvr in scan_ebuilds():
				if pvr not in self._packages:
					p = PackageInfo ( physical_only=True, pvr=pvr )
					self._packages [ p ['ebuild_verstr'] ] = p
	# --- end of scan (...) ---

	def show ( self, stream=sys.stderr ):
		"""Prints this dir (the ebuilds and the metadata) into a stream.

		arguments:
		* stream -- stream to use, defaults to sys.stderr

		returns: None (implicit)

		raises:
		* IOError
		"""
		return self.write ( shared_fh=stream )
	# --- end of show (...) ---

	def write ( self,
		shared_fh=None, overwrite_ebuilds=True,
		write_ebuilds=True, write_manifest=True, write_metadata=True
	):
		"""Writes this directory to its (existent!) filesystem location.

		arguments:
		* shared_fh         -- if set and not None: write everyting into <fh>
		* write_ebuilds     -- if set and False: don't write ebuilds
		* write_manifest    -- if set and False: don't write the Manifest file
		* write_metadata    -- if set and False: don't write the metadata file
		* overwrite_ebuilds -- if set and False: don't overwrite ebuilds

		returns: None (implicit)

		raises:
		* IOError (?)
		"""
		with self._lock:
			# mkdir not required here, overlay.Category does this

			# write ebuilds
			if write_ebuilds:
				self.write_ebuilds (
					overwrite=overwrite_ebuilds, shared_fh=shared_fh
				)

			# write metadata
			if write_metadata:
				self.write_metadata ( shared_fh=shared_fh )

			# write manifest (only if shared_fh is None)
			if write_manifest and shared_fh is None:
				self.write_manifest()
	# --- end of write (...) ---

	def write_ebuilds ( self, overwrite, shared_fh=None ):
		"""Writes all ebuilds.

		arguments:
		* shared_fh      -- if set and not None: don't use own file handles
		                     (i.e. write files), write everything into shared_fh
		* overwrite      -- write ebuilds that have been written before,
		                     defaults to True
		"""
		ebuild_header = self.get_header()

		def write_ebuild ( efile, ebuild ):
			"""Writes an ebuild.

			arguments:
			* efile  -- file to write
			* ebuild -- ebuild object to write (has to have a __str__ method)
			* (shared_fh from write_ebuilds())
			"""
			_success = False
			try:
				fh = open ( efile, 'w' ) if shared_fh is None else shared_fh
				if ebuild_header is not None:
					fh.write ( str ( ebuild_header ) )
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

		def ebuilds_to_write():
			"""Yields all ebuilds that are ready to be written."""

			for ver, p_info in self._packages.items():
				if p_info.has ( 'ebuild' ) and not p_info ['physical_only']:
					efile = self.ebuild_filepath_format.format ( PVR=ver )

					if efile != p_info ['ebuild_file'] or overwrite:
						yield ( efile, p_info )
					# else efile exists
		# --- end of ebuilds_to_write (...) ---

		all_ebuilds_written = True

		for efile, p_info in ebuilds_to_write():
			if write_ebuild ( efile, p_info ['ebuild'] ):
				self._need_manifest = True

				# update metadata for each successfully written ebuild
				#  (self._metadata knows how to handle this request)
				self._metadata.update ( p_info )

				if shared_fh is None:
					# this marks the package as 'written to fs'
					p_info.update_now (
						ebuild_file=efile,
						remove_auto='ebuild_written'
					)

					self.logger.info ( "Wrote ebuild {}.".format ( efile ) )
			else:
				all_ebuilds_written = False
				self.logger.error (
					"Couldn't write ebuild {}.".format ( efile )
				)

		self.modified = not all_ebuilds_written
		return all_ebuilds_written
	# --- end of write_ebuilds (...) ---

	def write_incremental ( self ):
		with self._lock:
			return self.write_ebuilds ( overwrite=False )
	# --- end of write_incremental (...) ---

	def write_manifest ( self ):
		"""Generates and writes the Manifest file for this package.

		expects: called after writing metadata/ebuilds

		returns: None (implicit)

		raises:
		* Exception if no ebuild exists
		"""

		# it should be sufficient to call create_manifest for one ebuild,
		#  choosing the latest one that exists in self.physical_location and
		#  has enough data (DISTDIR, EBUILD_FILE) for this task.
		#
		# metadata.xml's full path cannot be used for manifest creation here
		#  'cause DISTDIR would be unknown
		#

		# collect suitable PackageInfo instances
		pkgs_for_manifest = tuple (
			p for p in self._packages.values() \
				if p.has ( 'distdir', 'ebuild_file' )
		)

		if pkgs_for_manifest:
			manifest.create_manifest ( pkgs_for_manifest, nofail=False )
			self._need_manifest = False
		else:
			raise Exception (
				"No ebuild written so far! I really don't know what do to!"
			)
	# --- end of write_manifest (...) ---

	def write_metadata ( self, shared_fh=None ):
		"""Writes metadata for this package."""
		try:
			self.generate_metadata ( skip_if_existent=True )

			if shared_fh is None:
				if self._metadata.write():
					self._need_metadata = False
					self._need_manifest = True
					return True
				else:
					self.logger.error (
						"Failed to write metadata file {}.".format (
							self._metadata.filepath
						)
					)
					return False
			else:
				self._metadata.show ( shared_fh )
				return True
		except:
			# already logged
			return False
	# --- end of write_metadata (...) ---
