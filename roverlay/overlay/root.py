# R Overlay -- overlay module
# Copyright 2006-2012 Gentoo Foundation
# Distributed under the terms of the GNU General Public License v2

import threading
import logging
import shutil
import os

from roverlay import config, util

from roverlay.overlay.category import Category
from roverlay.overlay.header   import EbuildHeader

DEFAULT_USE_DESC = '\n'.join ( [
	'byte-compile - enable byte compiling',
	'R_suggests - install recommended packages'
] )


class Overlay ( object ):

	def __init__ (
		self,
		name, logger, directory,
		default_category, eclass_files,
		ebuild_header,
		incremental
	):
		if directory is None:
			raise Exception (
				"support for overlays without filesystem location has been dropped"
			)

		self.name              = name
		self.logger            = logger.getChild ( 'overlay' )
		self.physical_location = directory
		self.default_category  = default_category
		self.eclass_files      = eclass_files

		self.ignore_existing_ebuilds = False

		self._profiles_dir     = self.physical_location + os.sep + 'profiles'
		self._catlock          = threading.Lock()
		self._categories       = dict()
		self._header           = EbuildHeader ( ebuild_header )

		# fixme or ignore: calculating eclass names twice,
		# once here and another time when calling _init_overlay
		self._header.set_eclasses ( set (
			self._get_eclass_import_info ( only_eclass_names=True )
		) )

		self.incremental = incremental
		if self.incremental:

			self._incremental_write_lock = threading.Lock()
			self.scan()
			self._init_overlay ( reimport_eclass=True, make_profiles_dir=True )

	# --- end of __init__ (...) ---

	def scan ( self, **kw ):
		if os.path.isdir ( self.physical_location ):
			for cat in self._scan_categories():
				try:
					cat.scan ( **kw )
				except Exception as e:
					self.logger.exception ( e )
#		for package in sorted ( self.list_packages() ):
#			print ( package )
	# --- end of scan (...) ---

	def list_packages ( self, for_deprules=True ):
		for cat in self._categories.values():
			for package in cat.list_packages ( for_deprules=True ):
				yield package
	# --- end of list_packages (...) ---

	def list_rule_kwargs ( self ):
		for cat in self._categories.values():
			for kwargs in cat.list_packages ( for_deprules=True ):
				yield kwargs
	# --- end of list_rule_kwargs (...) ---

	def has_dir ( self, _dir ):
		return os.path.isdir ( self.physical_location + os.sep + _dir )
	# --- end of has_category (...) ---

	def _scan_categories ( self ):
		for x in os.listdir ( self.physical_location ):
			# FIXME could use a better check here
			if '-' in x and self.has_dir ( x ):
				yield self._get_category ( x )
	# --- end of _scan_categories (...) ---

	def _get_category ( self, category ):
		"""Returns a reference to the given category. Creates it if necessary.

		arguments:
		* category -- category identifier as string
		"""
		if not category in self._categories:
			self._catlock.acquire()
			try:
				if not category in self._categories:
					newcat = Category (
						category,
						self.logger,
						self.physical_location + os.sep + category,
						get_header=self._header.get,
						incremental=self.incremental
					)
					self._categories [category] = newcat
					if self.incremental:
						util.dodir ( newcat.physical_location )
			finally:
				self._catlock.release()

		return self._categories [category]
	# --- end of _get_category (...) ---

	def add ( self, package_info, category=None ):
		"""Adds a package to this overlay.

		arguments:
		* package_info -- PackageInfo of the package to add
		* category     -- category where the pkg should be put in, defaults to
		                   self.default_category

		returns: True if successfully added else False
		"""
		cat = self._get_category (
			self.default_category if category is None else category
		)
		return cat.add ( package_info )
	# --- end of add (...) ---

	def show ( self, **show_kw ):
		"""Presents the ebuilds/metadata stored in this overlay.

		arguments:
		* **show_kw -- keywords for package.PackageDir.show(...)

		returns: None (implicit)
		"""
		if not self._header.eclasses: self._header.set_eclasses (
			tuple ( self._get_eclass_import_info ( only_eclass_names=True ) )
		)
		for cat in self._categories.values():
			cat.show ( **show_kw )
	# --- end of show (...) ---

	def write ( self, **write_kw ):
		"""Writes the overlay to its physical location (filesystem), including
		metadata and Manifest files.

		arguments:
		* **write_kw -- keywords for package.PackageDir.write(...)

		returns: None (implicit)

		raises: IOError

		! TODO/FIXME/DOC: This is not thread-safe, it's expected to be called
		when ebuild creation is done.
		"""
		raise Exception ( "^,^" )
		# writing profiles/ here, rewriting categories/ later
		self._init_overlay ( reimport_eclass=True, make_profiles_dir=True )

		for cat in self._categories.values():
			if not cat.empty():
				util.dodir ( cat.physical_location )
				cat.write ( **write_kw )

		self._write_categories ( only_active=True )
	# --- end of write (...) ---

	def write_incremental ( self, **write_kw ):
		"""Writes all ebuilds that have been added since the last
		write_incremental call.
		TODO:
		* This could be useful to save some mem by removing already written
		package infos.
		* This has to be thread safe
		"""
		if not self._incremental_write_lock.acquire():
			# another incremental write is running, drop this request
			return

		try:
			util.dodir ( self.physical_location )
			cats = tuple ( self._categories.values() )
			for cat in cats:
				util.dodir ( cat.physical_location )
				cat.write_incremental ( **write_kw )
		finally:
			self._incremental_write_lock.release()
	# --- end of write_incremental (...) ---

	def finalize_write_incremental ( self ):
		"""Writes metadata + Manifest for all packages."""
		self._write_categories ( only_active=True )
		for cat in self._categories.values():
			cat.finalize_write_incremental()
	# --- end of finalize_incremental (...) ---

	def generate_metadata ( self, **metadata_kw ):
		"""Tells the overlay's categories to create metadata.
		You don't have to call this before write()/show() unless you want to use
		special metadata options.

		arguments:
		* **metadata_kw -- keywords for package.PackageDir.generate_metadata(...)

		returns: None (implicit)
		"""
		for cat in self._categories.values():
			cat.generate_metadata ( **metadata_kw )
	# --- end of generate_metadata (...) ---

	def generate_manifest ( self, **manifest_kw ):
		"""Generates Manifest files for all ebuilds in this overlay that exist
		physically/in filesystem.
		Manifest files are automatically created when calling write().

		arguments:
		* **manifest_kw -- see PackageDir.generate_manifest(...)

		returns: None (implicit)
		"""
		for cat in self._categories.values():
			cat.generate_manifest ( **manifest_kw )
	# --- end of generate_manifest (...) ---

	def _write_profiles_dir ( self, only_active_categories=True ):
		"""Creates and updates the profiles/ dir.

		arguments:
		* only_active_categories -- if True: do not list categories without
		                                      ebuilds in profiles/categories
		"""
		# profiles/
		util.dodir ( self._profiles_dir )
		self._write_repo_name()
		self._write_categories ( only_active=only_active_categories )
		self._write_usedesc()
	# --- end of _write_profiles_dir (...) ---

	def _write_profiles_file ( self, filename, to_write ):
		"""Writes a file in profiles/.

		arguments:
		* filename -- name of the file to write (including file extension)
		* to_write -- string to write (don't forget newline at the end)
		"""
		fh = None
		try:
			fh = open ( self._profiles_dir + os.sep + filename, 'w' )
			if to_write:
				# else touch file
				fh.write ( to_write )
		except IOError as e:
			self.logger.exception ( e )
			raise
		finally:
			if fh: fh.close()
	# --- end of _write_profiles_file (...) ---

	def _write_repo_name ( self ):
		"""Writes profiles/repo_name."""
		self._write_profiles_file ( 'repo_name', self.name + '\n' )
	# --- end of _write_repo_name (...) ---

	def _write_categories ( self, only_active=True ):
		"""Writes profiles/categories.

		arguments:
		* only_active -- exclude categories without ebuilds
		"""
		cats = None
		if only_active:
			cats = [
				name for name, category
					in self._categories.items() if not category.empty()
			]
		else:
			cats = list ( self._categories.keys() )

		if cats:
			self._write_profiles_file (
				'categories',
				'\n'.join ( cats ) + '\n'
			)
	# --- end of _write_categories (...) ---

	def _write_usedesc ( self ):
		"""Writes profiles/use.desc."""
		use_desc = config.get (
			'OVERLAY.use_desc',
			fallback_value=DEFAULT_USE_DESC
		)
		if use_desc:
			self._write_profiles_file ( 'use.desc', use_desc + '\n' )
	# --- end of _write_usedesc (...) ---

	def _get_eclass_import_info ( self, only_eclass_names=False ):
		"""Yields eclass import information (eclass names and files).

		arguments:
		* only_eclass_names -- if True: yield eclass dest names only,
		                       else   : yield (eclass name, eclass src file)
		                        Defaults to False.

		raises: AssertionError if a file does not end with '.eclass'.
		"""
		if self.eclass_files:

			for eclass in self.eclass_files:
				dest = os.path.splitext ( os.path.basename ( eclass ) )

				if dest[1] == '.eclass' or ( not dest[1] and not '.' in dest[0] ):
					if only_eclass_names:
						yield dest[0]
					else:
						yield ( dest[0], eclass )
				else:
					raise AssertionError (
						"{!r} does not end with '.eclass'!".format ( eclass )
					)
	# --- end of _get_eclass_import_info (...) ---

	def _import_eclass ( self, reimport_eclass ):
		"""Imports eclass files to the overlay. Also sets ebuild_names.

		arguments:
		* reimport_eclass -- whether to import existing eclass files (again)

		raises:
		* AssertionError, passed from _get_eclass_import_info()
		* Exception if copying fails
		"""

		if self.eclass_files:
			# import eclass files
			eclass_dir = self.physical_location + os.sep +  'eclass'
			try:
				eclass_names = list()
				util.dodir ( eclass_dir )

				for destname, eclass in self._get_eclass_import_info ( False ):
					dest = eclass_dir + os.sep +  destname + '.eclass'
					if reimport_eclass or not os.path.isfile ( dest ):
						shutil.copyfile ( eclass, dest )

					eclass_names.append ( destname )

				self._header.set_eclasses ( frozenset ( eclass_names ) )

			except Exception as e:
				self.logger.critical ( "Cannot import eclass files!" )
				raise
	# --- end of _import_eclass (...) ---

	def _init_overlay ( self, reimport_eclass, make_profiles_dir ):
		"""Initializes the overlay at its physical/filesystem location.

		arguments:
		* reimport_eclass   -- whether to copy existing eclass files
		                         again (True) or not
		* make_profiles_dir -- if True: create the profiles/ dir now

		raises:
		* IOError
		"""
		try:
			# mkdir overlay root
			util.dodir ( self.physical_location, mkdir_p=True )

			self._import_eclass ( reimport_eclass )

			if make_profiles_dir:
				self._write_profiles_dir ( only_active_categories=False )

		except IOError as e:

			self.logger.exception ( e )
			self.logger.critical ( "^failed to init overlay" )
			raise
	# --- end of _init_overlay (...) ---