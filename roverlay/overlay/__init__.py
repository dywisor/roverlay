# R Overlay -- <comment TODO>
# Copyright 2006-2012 Gentoo Foundation
# Distributed under the terms of the GNU General Public License v2

import threading
import logging
import shutil
import os

from roverlay import config, util

from roverlay.overlay.category import Category

DEFAULT_USE_DESC = '\n'.join ( [
	'byte-compile - enable byte compiling',
	'R_suggests - install recommended packages'
] )

class Overlay ( object ):

	def __init__ (
		self,
		name=None,
		logger=None,
		directory=None,
		default_category=None,
		eclass_files=None
	):

		# not setting any default values here (currently)

		if name is None:
			self.name = config.get_or_fail ( 'OVERLAY.name' )
		else:
			self.name = name

		if logger is None:
			#self.logger = logging.getLogger ( self.name )
			self.logger = logging.getLogger ( 'overlay' )
		else:
			#self.logger = logger.getChild ( self.name )
			self.logger = logger.getChild ( 'overlay' )

		if directory is None:
			self.physical_location = config.get_or_fail ( 'OVERLAY.dir' )
		else:
			self.physical_location = directory

		if default_category is None:
			self.default_category = config.get_or_fail ( 'OVERLAY.category' )
		else:
			self.default_category = default_category


		if eclass_files is None:
			eclass_files = config.get ( 'OVERLAY.eclass_files', None )

		if isinstance ( eclass_files, str ):
			self.eclass_files = frozenset ( eclass_files )
		else:
			self.eclass_files = eclass_files


		#
		self._profiles_dir = os.path.join ( self.physical_location, 'profiles' )

		self._catlock        = threading.Lock()
		self._categories     = dict()
		self._default_header = config.get ( 'EBUILD.default_header', None )
	# --- end of __init__ (...) ---

	def _get_category ( self, category ):
		"""Returns a reference to the given category. Creates it if necessary.

		arguments:
		* category -- category identifier as string
		"""
		if not category in self._categories:
			self._catlock.acquire()
			if not category in self._categories:
				self._categories [category] = Category (
					category,
					self.logger,
					None if self.physical_location is None else \
						os.path.join ( self.physical_location, category )
				)
			self._catlock.release()

		return self._categories [category]
	# --- end of _get_category (...) ---

	def add ( self, package_info, category=None ):
		"""Adds a package to this overlay.

		arguments:
		* package_info -- PackageInfo of the package to add
		* category     -- category where the pkg should be put in, defaults to
		                   self.default_category

		returns: None (implicit)
		"""
		self._get_category (
			self.default_category if category is None else category
		) . add ( package_info )
	# --- end of add (...) ---

	def show ( self, **show_kw ):
		"""Presents the ebuilds/metadata stored in this overlay.

		arguments:
		* **show_kw -- ignored! (keywords for package.PackageDir.show(...))

		returns: None (implicit)
		"""
		for cat in self._categories.values():
			cat.show ( default_header=self._default_header )
	# --- end of show (...) ---

	def write ( self, **write_kw ):
		"""Writes the overlay to its physical location (filesystem), including
		metadata and Manifest files.
		TODO include Manifest generation in package.py

		arguments:
		* **write_kw -- ignored! (keywords for package.PackageDir.write(...))

		returns: None (implicit)

		raises: !! TODO

		TODO/FIXME/DOC: This is not thread-safe, it's expected to be called
		when ebuild creation is done.
		"""
		# writing profiles/ here, rewriting categories/ later
		self._init_overlay ( reimport_eclass=True, make_profiles_dir=True )

		for cat in self._categories.values():
			if cat.physical_location and not cat.empty():
				util.dodir ( cat.physical_location )
				cat.write ( default_header=self._default_header )

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
		raise Exception ( "method stub" )
	# --- end of write_incremental (...) ---

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
			fh = open ( os.path.join ( self._profiles_dir, filename ), 'w' )
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
		# TODO: config entry
		use_desc = config.get (
			'OVERLAY.use_desc',
			fallback_value=DEFAULT_USE_DESC
		)
		if use_desc:
			self._write_profiles_file ( 'use.desc', use_desc + '\n' )
	# --- end of _write_usedesc (...) ---

	def _import_eclass ( self, reimport_eclass ):

		if self.eclass_files:
			# import eclass files
			eclass_dir = os.path.join ( self.physical_location, 'eclass' )
			try:
				util.dodir ( eclass_dir )

				for eclass in self.eclass_files:
					src  = eclass
					dest = None
					if isinstance ( eclass, str ):
						dest = os.path.basename ( eclass )
					else:
						# list-like specification ( src, destname )
						src  = eclass [0]
						dest = eclass [1]

					dest = os.path.join ( eclass_dir, dest )

					if reimport_eclass or not os.path.isfile ( dest ):
						shutil.copyfile ( src, dest )


			except Exception as e:
				#self.logger.exception ( e ) TODO try-catch blocks
				self.logger.critical ( "Cannot import eclass files!" )
				raise
	# --- end of _import_eclass (...) ---

	def _init_overlay ( self, reimport_eclass=False, make_profiles_dir=False ):
		"""Initializes the overlay at its physical/filesystem location.

		arguments:
		* reimport_eclass   -- whether to copy existing eclass files
		                         again (True) or not
		* make_profiles_dir -- if True: create the profiles/ dir now

		raises:
		* Exception if no physical location assigned
		* <TODO> passes IOError,...
		"""
		if self.physical_location is None:
			raise Exception ( "no directory assigned." )

		try:
			# mkdir overlay root
			os.makedirs ( self.physical_location, exist_ok=True ) # raises?

			self._import_eclass ( reimport_eclass )

			if make_profiles_dir:
				self._write_profiles_dir ( only_active_categories=False )

		except IOError as e:

			self.logger.exception ( e )
			self.logger.critical ( "^failed to init overlay" )
			raise







