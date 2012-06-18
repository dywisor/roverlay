# R Overlay -- <comment TODO>
# Copyright 2006-2012 Gentoo Foundation
# Distributed under the terms of the GNU General Public License v2

import threading
import os.path
import sys

from roverlay.portage.metadata.creation import MetadataJob

SUPPRESS_EXCEPTIONS = True

class PackageDir ( object ):

	# TODO: do Manifest creation here

	def __init__ ( self, name, logger, directory ):
		self.logger            = logger.getChild ( name )
		# Lock or RLock? (TODO)
		self._lock             = threading.RLock()
		self._packages         = dict()
		self._metadata         = None
		self.physical_location = directory
	# --- end of __init__ (...) ---

	def empty ( self ):
		return len ( self._packages ) == 0

	def set_fs_location ( self, directory ):
		self.physical_location = directory

	def _get_metadata_filepath ( self ):
		return os.path.join (
			'??' if self.physical_location is None else self.physical_location,
			self._metadata.filename
		)
	# --- end of _get_metadata_filepath (...) ---

	def _get_ebuild_filepath ( self, pvr ):
		filename = "%s-%s.ebuild" % ( self.name, pvr )
		return os.path.join (
			'??' if self.physical_location is None else self.physical_location,
			filename
		)
	# --- end of _get_ebuild_filepath (...) ---

	def write ( self ):
		if self.physical_location is None:
			raise Exception ( "cannot write - no directory assigned!" )

		self._lock.acquire()
		self._regen_metadata()

		# mkdir not required here, overlay.Category does this

		for ver, p_info in self._packages.items():
			fh = None
			try:
				efile  = self._get_ebuild_filepath ( ver )
				ebuild = p_info.ebuild

				fh = open ( efile, 'w' )
				ebuild.write ( fh )

				# adjust owner/perm? TODO
				# chmod 0644 or 0444
				# chown 250.250

				self.logger.info ( "Wrote ebuild %s." % efile )
			except IOError as e:
				self.logger.error ( "Couldn't write ebuild %s." % efile )
				self.logger.exception ( e )

			finally:
				if fh: fh.close()
				fh = None

		fh = None
		try:
			mfile = self._get_metadata_filepath()

			fh    = open ( mfile, 'w' )
			self._metadata.write ( fh )

		except IOError as e:
			self.logger.error ( "Failed to write metadata at %s." % mfile )
			self.logger.exception ( e )
		finally:
			if fh: fh.close()
			del fh

		# !! TODO write Manifest here

		self._lock.release()
	# --- end of write (...) ---

	def show ( self, stream=sys.stderr ):
		self._lock.acquire()
		self._regen_metadata()


		for ver, p_info in self._packages.items():
			efile  = self._get_ebuild_filepath ( ver )
			ebuild = p_info.ebuild

			stream.write ( "[BEGIN ebuild %s]\n" % efile )
			ebuild.write ( stream )
			stream.write ( "[END ebuild %s]\n" % efile )

		mfile = self._get_metadata_filepath()

		stream.write ( "[BEGIN %s]\n" % mfile )
		self._metadata.write ( stream )
		stream.write ( "[END %s]\n" % mfile )


		self._lock.release()

	def _latest_package ( self ):
		"""Returns the package info with the highest version number."""
		first  = True
		retver = None
		retpkg = None
		for p in self._packages.values():
			newver = p ['version']
			if first or newver > retver:
				retver = newver
				retpkg = p
				first  = False

		return retpkg
	# --- end of _latest_package (...) ---

	def add ( self, package_info ):
		# !! p info key TODO
		shortver = package_info ['ebuild_verstr']

		def already_exists ( release=False ):
			if filename in self._packages:

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
	# --- end of add (...) ---

	def _regen_metadata ( self ):
		self.generate_metadata (
			skip_if_existent=True,
			use_all_packages=True,
			use_old_metadata=False
		)

	def generate_metadata (
		self,
		skip_if_existent=False, use_all_packages=False, use_old_metadata=False
	):
		if skip_if_existent and not self._metadata is None:
			return

		self._lock.acquire()

		if not use_old_metadata or self._metadata is None:
			del self._metadata
			self._metadata = MetadataJob ( self.logger )

		if use_all_packages:
			for p_info in self._packages:
				self._metadata.update ( p_info )
		else:
			self._metadata.update ( _latest_package() )


		self._lock.release()

	def _flist ( self ):
		files = list()
		if not self._metadata is None:
			files.append ( self._metadata.filename )

		for ver in self._packages:
			files.append ( "%s-%s.ebuild" % ( self.name, ver ) )

		return files
	# --- end of _flist (...) ---

	def ls ( self ):
		return frozenset ( self._flist() )
	# --- end of ls (...) ---

	def lslong ( self ):
		return frozenset ( ( os.path.join (
			'??' if self.physical_location is None else self.physical_location,
			f
		) for f in self._flist() ) )
	# --- end of lslong (...) ---

	def __str__ ( self ): return '\n'.join ( self.ls() )



