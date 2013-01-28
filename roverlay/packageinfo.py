# R overlay -- roverlay package, packageinfo
# -*- coding: utf-8 -*-
# Copyright (C) 2012 André Erdmann <dywi@mailerd.de>
# Distributed under the terms of the GNU General Public License;
# either version 2 of the License, or (at your option) any later version.

"""package info data structure

This module provides one class, PackageInfo, which is a data structure that
offers access to package and ebuild related data. It's also able to calculate
some data if required, like getting description data from an R package.
"""

__all__ = [ 'PackageInfo', ]

import re
import os.path
import logging
import threading

from roverlay          import config, strutil
from roverlay.rpackage import descriptionreader

#
# PackageInfo keys known to be used (read) in the roverlay modules:
#
# * desc_data        in ebuild/creation, metadata/__init__
# * distdir          in manifest/helpers
# * ebuild           in overlay/package
# * ebuild_file      in manifest/helpers, overlay/package
# * ebuild_verstr    in overlay/package
# * name             in ebuild/creation, overlay/category
# * package_file     in rpackage/descriptionreader
# * package_name     in rpackage/descriptionreader
# * package_url      in ebuild/creation
# * physical_only    in overlay/pacakge
# * version          in ebuild/package (as tuple)
#

LOGGER = logging.getLogger ( 'PackageInfo' )

class PackageInfo ( object ):
	"""PackageInfo offers easy, subscriptable access to package
	information, whether stored or calculated.

	class-wide variables:
	* EBUILDVER_REGEX -- a regex containing chars that will be replaced by
	                     a dot '.'. (e.g. 2-3 becomes 2.3)
	* PKGSUFFIX_REGEX -- a regex that matches the suffix of an R package file
	                     name. The regex str is retrieved from the config
	                     module (which also means that the config has to be
	                     loaded before import this module)
	* ALWAYS_FALLBACK -- a set of keys for which get() always returns a
	                     fallback value (None)

	* _UPDATE_KEYS_SIMPLE         -- a set of keys that can be added
	                                 without further checks
	* _UPDATE_KEYS_SIMPLE_INITIAL -- like _UPDATE_KEYS_SIMPLE, but only used
	                                 on the first update() call (as long as
	                                 no keys have been stored)
	* _UPDATE_KEYS_FILTER_NONE    -- like _UPDATE_KEYS_SIMPLE, but stores
	                                 key's value only if it is not None
	* _REMOVE_KEYS_KEEP_EBUILD    -- a set of keys that will be kept when
	                                 _remove_auto ( 'ebuild_written' ) is
	                                 called.
	                                 These keys must exist at this point!
	"""

	EBUILDVER_REGEX = re.compile ( '[-]{1,}' )
	PKGSUFFIX_REGEX = re.compile (
		config.get_or_fail ( 'R_PACKAGE.suffix_regex' ) + '$'
	)
	ALWAYS_FALLBACK = frozenset ( ( 'ebuild', 'ebuild_file' ) )

	_UPDATE_KEYS_SIMPLE         = frozenset ((
		'origin',
		'ebuild',
		'ebuild_file',
		'physical_only',
		'src_uri',
	))
	_UPDATE_KEYS_SIMPLE_INITIAL = frozenset ((
		'package_filename',
	))
	_UPDATE_KEYS_FILTER_NONE    = frozenset ((
		'src_uri_base',
		'distdir',
	))

	_REMOVE_KEYS_KEEP_EBUILD    = frozenset ((
		'distdir', 'desc_data', 'ebuild_file', 'version',
		'ebuild_filename', 'package_name', 'package_filename',
	))

	def __init__ ( self, **initial_info ):
		"""Initializes a PackageInfo.

		arguments:
		* **initial_info -- passed to update ( **kw )
		"""
		self._info               = dict()
		self.readonly            = False
		self._update_lock        = threading.RLock()
		self.overlay_package_ref = None
		self.logger              = LOGGER

		self.update ( **initial_info )
	# --- end of __init__ (...) ---

	def set_readonly ( self, immediate=False, final=False ):
		"""Makes the package info readonly.

		arguments:
		* immediate -- do not acquire lock, set readonly directly,
		                defaults to False
		* final     -- if set and True: make this decision final
	  """
		self._set_mode ( True, immediate, final )
	# --- end of set_readonly (...) ---

	def set_writeable ( self, immediate=False ):
		"""Makes the package info writeable.

		arguments:
		* immediate -- do not acquire lock, set writeable directly,
		                defaults to False
		"""
		self._set_mode ( False, immediate )
	# --- end of set_writeable (...) ---

	def _set_mode ( self, readonly_val, immediate=False, final=False ):
		"""Sets readonly to True/False.

		arguments:
		* readonly_val -- new value for readonly
		* immediate    -- do not acquire lock
		* final        -- only if readonly_val is True: make this decision final,

		raises: Exception if self.readonly is a constant (_readonly_final is set)
		"""
		if hasattr ( self, '_readonly_final' ):
			raise Exception ( "cannot modify readonly - it's a constant." )
		elif immediate:
			self.readonly = readonly_val
			if final and readonly_val:
				self._readonly_final = True
		elif not self.readonly is readonly_val:
			self._update_lock.acquire()
			self.readonly = readonly_val
			if final and readonly_val:
				self._readonly_final = True
			self._update_lock.release()
	# --- end of _set_mode (...) ---

	def _writelock_acquire ( self ):
		"""Acquires the lock required for adding new information.

		raises: Exception if readonly (writing not allowed)
		"""
		if self.readonly or hasattr ( self, '_readonly_final' ):
			raise Exception ( "package info is readonly!" )

		self._update_lock.acquire()

		if self.readonly or hasattr ( self, '_readonly_final' ):
			self._update_lock.release()
			raise Exception ( "package info is readonly!" )

		return True
	# --- end of _writelock_acquire (...) ---

	def has_key ( self, *keys ):
		"""Returns False if at least one key out of keys is not accessible,
		i.e. its data cannot be retrieved using get()/__getitem__().

		arguments:
		* *keys -- keys to check
		"""
		for k in keys:
			if k not in self._info:
				# try harder - use get() with fallback value to see if value
				# can be calculated
				if self.get ( k, do_fallback=True ) is None:
					return False
		return True
	# --- end of has_key (...) ---

	has = has_key

	def has_key_or ( self, *keys ):
		"""Returns True if at least one key out of keys is accessible.

		arguments:
		* *keys -- keys to check
		"""
		for k in keys:
			if k in self._info:
				return True
			elif self.get ( k, do_fallback=True ) is not None:
				return True
		return False
	# --- end of has_key_or (...) ---

	has_or = has_key_or

	def compare_version ( self, other_package ):
		"""Compares the version of two PackageInfo objects.
		Returns 1 if self's version is higher, -1 if lower and 0 if equal.

		arguments:
		* other_package --
		"""
		if other_package is None: return 1

		my_ver    = self.get ( 'version', fallback_value=0 )
		other_ver = other_package.get ( 'version', fallback_value=0 )

		if my_ver > other_ver:
			return 1
		elif my_ver == other_ver:
			return 0
		else:
			return -1
	# --- end of compare_version (...) ---

	def get ( self, key, fallback_value=None, do_fallback=False ):
		"""Returns the value specified by key.
		The value is either calculated or taken from dict self._info.

		arguments:
		* key --
		* fallback_value -- fallback value if key not found / unknown
		* do_fallback    -- if True: return fallback_value, else raise KeyError

		raises: KeyError
		"""
		# normal dict access shouldn't be slowed down here
		if key in self._info: return self._info [key]

		key_low = key.lower()

		if key_low in self._info:
			return self._info [key_low]

		# 'virtual' keys - calculate result
		elif key_low == 'name':
			# no special name, using package_name
			return self._info ['package_name']

		elif key_low == 'package_file':
			# assuming that origin is in self._info
			return os.path.join (
				self.get ( 'distdir' ),
				self._info ['package_filename']
			)

		elif key_low == 'distdir':
			if 'origin' in self._info:
				# this doesn't work if the package is in a sub directory
				# of the repo's distdir
				return self._info ['origin'].distdir
			elif 'package_file' in self._info:
				return os.path.dirname ( self._info ['package_file'] )
			# else fallback/KeyError

		elif key_low == 'has_suggests':
			# 'has_suggests' not in self._info -> assume False
			return False

		elif key_low == 'physical_only':
			# 'physical_only' not in self._info -> assume False
			return False

		elif key_low == 'src_uri':
			if 'src_uri_base' in self._info:
				return \
					self._info ['src_uri_base'] + '/' + \
					self._info ['package_filename']

			elif 'origin' in self._info:
				return self._info ['origin'].get_src_uri (
					self._info ['package_filename']
				)
			else:
				return "http://localhost/R-packages/" + \
					self._info ['package_filename']

		elif key_low == 'ebuild_dir':
			ebuild_file = self._info ['ebuild_file']
			if ebuild_file is not None:
				return os.path.dirname ( ebuild_file )

		elif key_low == 'ebuild_filename':
			ebuild_file = self._info ['ebuild_file']
			if ebuild_file is not None:
				return os.path.basename ( ebuild_file )

		# end if <key matches ...>


		# fallback
		if do_fallback or fallback_value is not None:
			return fallback_value

		elif key_low in self.__class__.ALWAYS_FALLBACK:
			return None

		else:
			raise KeyError ( key )
	# --- end of get (...) ---

	def get_desc_data ( self ):
		"""Returns the DESCRIPTION data for this PackageInfo (by reading the
		R package file if necessary).
		"""
		if 'desc_data' in self._info:
			return self._info ['desc_data']

		self._writelock_acquire()
		if 'desc_data' not in self._info:
			self._info ['desc_data'] = descriptionreader.read ( self )

		self._update_lock.release()
		return self._info ['desc_data']
	# --- end of get_desc_data (...) ---

	def __getitem__ ( self, key ):
		"""Returns an item."""
		return self.get ( key, do_fallback=False )
	# --- end of __getitem__ (...) ---

	def __setitem__ ( self, key, value ):
		"""Sets an item.

		arguments:
		* key --
		* value --

		raises: Exception when readonly
		"""
		self._writelock_acquire()
		self._info [key] = value
		self._update_lock.release()
	# --- end of __setitem__ (...) ---

	def update_now ( self, **info ):
		"""Updates the package info data with temporarily enabling write access.
		Data will be readonly after calling this method.

		arguments:
		* **info --
		"""
		if len ( info ) == 0: return
		with self._update_lock:
			self.set_writeable()
			self.update ( **info )
			self.set_readonly()
	# --- end of update_now (...) ---

	def update ( self, **info ):
		"""Uses **info to update the package info data.

		arguments:
		* **info --

		raises: Exception when readonly
		"""
		if len ( info ) == 0:
			# nothing to do
			return

		initial = len ( self._info ) == 0

		# remove_auto has to be the last action (keyword order is not "stable")
		remove_auto = info.pop ( 'remove_auto', None )

		self._writelock_acquire()

		for key, value in info.items():

			if key in self.__class__._UPDATE_KEYS_SIMPLE:
				self [key] = value

			elif initial and key in self.__class__._UPDATE_KEYS_SIMPLE_INITIAL:
				self [key] = value

			elif key in self.__class__._UPDATE_KEYS_FILTER_NONE:
				if value is not None:
					self [key] = value

			elif key == 'filename':
				self._use_filename ( value )

			elif key == 'pvr':
				self._use_pvr ( value )

			elif key == 'suggests':
				self ['has_suggests'] = value

			elif key == 'depres_result':
				self ['has_suggests'] = value [2]

			elif key == 'filepath':
				self._use_filepath ( value )

			elif key == 'remove':
				for k in value:
					try:
						if k in self._info: del self._info [k]
					except KeyError:
						pass

			elif key == 'make_desc_data':
				if value:
					self.get_desc_data()

			else:
				self.logger.error (
					"in update(): unknown info key {}!".format ( key )
				)
		# -- end for;

		if remove_auto:
			self._remove_auto ( remove_auto )

		self._update_lock.release()
	# --- end of update (**kw) ---

	def _use_filename ( self, _filename ):
		"""auxiliary method for update(**kw)

		arguments:
		* _filename --
		"""
		filename_with_ext = _filename

		# remove .tar.gz .tar.bz2 etc.
		filename = PackageInfo.PKGSUFFIX_REGEX.sub ( '', filename_with_ext )

		self.logger = logging.getLogger ( filename )

		package_name, sepa, package_version = filename.partition (
			config.get ( 'R_PACKAGE.name_ver_separator', '_' )
		)

		if not sepa:
			# file name unexpected, tarball extraction will (probably) fail
			self.logger.error ( "unexpected file name {!r}.".format ( filename ) )
			raise Exception   ( "cannot use file {!r}.".format ( filename ) )
			return

		version_str = PackageInfo.EBUILDVER_REGEX.sub ( '.', package_version )

		try:
			version = tuple ( int ( z ) for z in version_str.split ( '.' ) )
			self ['version'] = version
		except ValueError as ve:
			# version string is malformed, cannot use it
			self.logger.error (
				"Cannot parse version string {!r} for {!r}".format (
					_filename, version_str
				)
			)
			raise

		# using package name as name (unless modified later),
		#  using pkg_version for the ebuild version

		# removing illegal chars from the package_name
		ebuild_name = strutil.fix_ebuild_name ( package_name )

		if ebuild_name != package_name:
			self ['name'] = ebuild_name

		self ['ebuild_verstr']    = version_str

		# for DescriptionReader
		self ['package_name']     = package_name

		self ['package_filename'] = filename_with_ext
	# --- end of _use_filename (...) ---

	def _use_pvr ( self, pvr ):
		# 0.1_pre2-r17 -> ( 0, 1 )
		pv = pvr.partition ( '-' ) [0]
		self ['version'] = tuple (
			int ( z ) for z in ( pv.partition ( '_' ) [0].split ( '.' ) )
		)
		self ['ebuild_verstr'] = pvr
	# --- end of _use_pvr (...) ---

	def _remove_auto ( self, ebuild_status ):
		"""Removes all keys from this PackageInfo instance that are useless
		after entering status 'ebuild_status' (like ebuild in overlay and
		written -> don't need the ebuild string etc.)
		"""
		with self._update_lock:

			if ebuild_status == 'ebuild_written':
				# selectively copying required keys to a new info dict

				to_keep = self.__class__._REMOVE_KEYS_KEEP_EBUILD

				# needs python >= 2.7
				info_new = { k : self.get ( k ) for k in to_keep }

				# also add an ebuild stub to the new dict to indicate
				# that this PackageInfo instance has been created from been
				# created from an R package in this script run
				info_new ['ebuild'] = True

				if 'physical_only' in self._info:
					info_new ['physical_only'] = self._info ['physical_only']

				info_old   = self._info
				self._info = info_new
				del info_old
			# -- if
		# -- lock
	# --- end of _remove_auto (...) ---

	def _use_filepath ( self, _filepath ):
		"""auxiliary method for update(**kw)

		arguments:
		* _filepath --
		"""
		self.logger.warn (
			'Please note that _use_filepath is only meant for testing.'
		)
		filepath = os.path.abspath ( _filepath )
		self ['package_file'] = filepath
		self._use_filename ( os.path.basename ( filepath ) )
	# --- end of _use_filepath (...) ---

	def __str__ ( self ):
		return "<PackageInfo for {pkg}>".format (
			pkg=self.get (
				'package_file', fallback_value='[unknown file]', do_fallback=True
		) )
	# --- end of __str__ (...) ---
