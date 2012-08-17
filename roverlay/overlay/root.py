# R overlay -- overlay package, overlay root
# -*- coding: utf-8 -*-
# Copyright (C) 2012 André Erdmann <dywi@mailerd.de>
# Distributed under the terms of the GNU General Public License;
# either version 2 of the License, or (at your option) any later version.

"""overlay <-> filesystem interface (root)

This module provides the Overlay class that acts as an interface between
PackageInfo instances (in memory) and the R overlay (directory in filesystem).
Most requests are redirected to its subdirectories (Category), which, in turn,
pass them to their subdirectories (PackageDir).

Caution: Never deep-copy an overlay object. This leads to infinite recursion
due do double-linkage between PackageInfo and PackageDir.
"""

__all__ = [ 'Overlay', ]

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
		name,
		logger,
		directory,
		default_category,
		eclass_files,
		ebuild_header,
		write_allowed,
		incremental,
		skip_manifest,
		runtime_incremental=False
	):
		"""Initializes an overlay.

		arguments:
		* name                -- name of this overlay
		* logger              -- parent logger to use
		* directory           -- filesystem location of this overlay
		* default_category    -- category of packages being added without a
		                          specific category
		* eclass_files        -- eclass files to import and
		                          inherit in all ebuilds
		* ebuild_header       -- the header text included in all created ebuilds
		* write_allowed       -- whether writing is allowed
		* incremental         -- enable/disable incremental writing:
		                         use already existing ebuilds (don't recreate
		                         them)
		* skip_manifest       -- skip Manifest generation to save time
		                         !!! The created overlay cannot be used with
		                         emerge/portage
		* runtime_incremental -- see package.py:PackageDir.__init__ (...),
		                          Defaults to False (saves memory but costs time)

		"""
		self.name                 = name
		self.logger               = logger.getChild ( 'overlay' )
		self.physical_location    = directory
		self.default_category     = default_category

		self._eclass_files        = eclass_files
		#self._incremental         = incremental
		# disable runtime_incremental if writing not allowed
		self._runtime_incremental = write_allowed and runtime_incremental
		self._writeable           = write_allowed

		self._profiles_dir        = self.physical_location + os.sep + 'profiles'
		self._catlock             = threading.Lock()
		self._categories          = dict()
		self._header              = EbuildHeader ( ebuild_header )

		self.skip_manifest        = skip_manifest

		# calculating eclass names twice,
		# once here and another time when calling _init_overlay
		self._header.set_eclasses ( frozenset (
			self._get_eclass_import_info ( only_eclass_names=True )
		) )

		#if self._incremental:
		if incremental:
			# this is multiple-run incremental writing (in contrast to runtime
			# incremental writing, which writes ebuilds as soon as they're
			# ready)
			self.scan()
	# --- end of __init__ (...) ---

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
						runtime_incremental=self._runtime_incremental
					)
					self._categories [category] = newcat
			finally:
				self._catlock.release()

		return self._categories [category]
	# --- end of _get_category (...) ---

	def _get_eclass_import_info ( self, only_eclass_names=False ):
		"""Yields eclass import information (eclass names and files).

		arguments:
		* only_eclass_names -- if True: yield eclass dest names only,
		                       else   : yield (eclass name, eclass src file)
		                        Defaults to False.

		raises: AssertionError if a file does not end with '.eclass'.
		"""
		if self._eclass_files:

			for eclass in self._eclass_files:
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

		if self._eclass_files:
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

	def _init_overlay ( self, reimport_eclass ):
		"""Initializes the overlay at its physical/filesystem location.

		arguments:
		* reimport_eclass   -- whether to copy existing eclass files
		                         again (True) or not
		* make_profiles_dir -- if True: create the profiles/ dir now

		raises:
		* IOError
		"""
		def write_profiles_dir():
			"""Creates and updates the profiles/ dir."""
			def write_profiles_file ( filename, to_write ):
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
			# --- end of write_profiles_file (...) ---

			# always use the default category (+write it into profiles/categories)
			self._get_category ( self.default_category )

			# profiles/
			util.dodir ( self._profiles_dir )

			# profiless/repo_name
			write_profiles_file ( 'repo_name', self.name + '\n' )

			# profiles/categories
			cats = '\n'.join ( self._categories.keys() )
			if cats:
				write_profiles_file ( 'categories', cats + '\n' )

			# profiles/use.desc
			use_desc = config.get (
				'OVERLAY.use_desc',
				fallback_value=DEFAULT_USE_DESC
			)
			if use_desc:
				write_profiles_file ( 'use.desc', use_desc + '\n' )
		# --- end of write_profiles_dir (...) ---

		try:
			# mkdir overlay root
			util.dodir ( self.physical_location, mkdir_p=True )

			self._import_eclass ( reimport_eclass )

			write_profiles_dir()

		except IOError as e:

			self.logger.exception ( e )
			self.logger.critical ( "^failed to init overlay" )
			raise
	# --- end of _init_overlay (...) ---

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

	def has_dir ( self, _dir ):
		return os.path.isdir ( self.physical_location + os.sep + _dir )
	# --- end of has_category (...) ---

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

	def readonly ( self ):
		return not self._writeable
	# --- end of readonly (...) ---

	def scan ( self, **kw ):
		def scan_categories():
			for x in os.listdir ( self.physical_location ):
				if '-' in x and self.has_dir ( x ):
					yield self._get_category ( x )
		# --- end of scan_categories (...) ---

		if os.path.isdir ( self.physical_location ):
			for cat in scan_categories():
				try:
					cat.scan ( **kw )
				except Exception as e:
					self.logger.exception ( e )
	# --- end of scan (...) ---

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

	def writeable ( self ):
		return self._writeable
	# --- end of writeable (...) ---

	def write ( self ):
		"""Writes the overlay to its physical location (filesystem), including
		metadata and Manifest files as well as cleanup actions.

		arguments:
		* **write_kw -- keywords for package.PackageDir.write(...)

		returns: None (implicit)

		raises: IOError

		Note: This is not thread-safe, it's expected to be called when
		ebuild creation is done.
		"""
		if self._writeable:
			self._init_overlay ( reimport_eclass=True )

			for cat in self._categories.values():
				cat.write (
					overwrite_ebuilds = False,
					keep_n_ebuilds    = config.get ( 'OVERLAY.keep_nth_latest', None ),
					cautious          = True,
					write_manifest    = not self.skip_manifest
				)
		else:
			# FIXME debug print
			print (
				"Dropped write request for readonly overlay {}!".format (
					self.name
			) )
	# --- end of write (...) ---

	def write_manifest ( self, **manifest_kw ):
		"""Generates Manifest files for all ebuilds in this overlay that exist
		physically/in filesystem.
		Manifest files are automatically created when calling write().

		arguments:
		* **manifest_kw -- see PackageDir.generate_manifest(...)

		returns: None (implicit)
		"""
		if self._writeable and not self.skip_manifest:
			# profiles/categories is required for successful Manifest
			# creation
			if os.path.isfile ( self._profiles_dir + os.sep + 'categories' ):
				for cat in self._categories.values():
					cat.write_manifest ( **manifest_kw )
			else:
				raise Exception (
					'profiles/categories is missing - cannot write Manifest files!'
				)
		elif not self.skip_manifest:
			# FIXME debug print
			print (
				"Dropped write_manifest request for readonly overlay {}!".format (
					self.name
			) )
	# --- end of write_manifest (...) ---
