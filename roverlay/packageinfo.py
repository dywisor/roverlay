# R Overlay -- package info class
# Copyright 2006-2012 Gentoo Foundation
# Distributed under the terms of the GNU General Public License v2

import re
import os.path
import logging
import threading

from roverlay import config, util

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
# * version          in ebuild/package (as tuple)
#

LOGGER = logging.getLogger ( 'PackageInfo' )

VIRTUAL_KEYS = dict (
	SRC_URI         = frozenset ( ( 'src_uri', 'package_url' ) ),
	ALWAYS_FALLBACK = frozenset ( ( 'ebuild', 'ebuild_file' ) ),
)

class PackageInfo ( object ):
	"""PackageInfo offers easy, subscriptable (['sth']) access to package
	information, whether stored or calculated.
	"""

	EBUILDVER_REGEX = re.compile ( '[-]{1,}' )
	PKGSUFFIX_REGEX = re.compile (
		config.get_or_fail ( 'R_PACKAGE.suffix_regex' ) + '$'
	)

	def __init__ ( self, **initial_info ):
		"""Initializes a PackageInfo.

		arguments:
		* **initial_info -- passed to update ( **kw )
		"""
		self._info        = dict()
		self.readonly     = False
		self._update_lock = threading.RLock()

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
			else:
				return os.path.dirname ( self._info ['package_file'] )

		elif key_low == 'has_suggests':
			if 'has_suggests' in self._info:
				return self._info ['has_suggests']

			else:
				return False

		elif key_low in VIRTUAL_KEYS ['SRC_URI']:
			# comment from ebuildjob:
			## origin is todo (sync module knows the package origin)
			## could calculate SRC_URI in the eclass depending on origin
			# comment from ebuild:
			## calculate SRC_URI using self._data ['origin'],
			## either here or in eclass

			#return "**packageinfo needs information from sync module!"

			if 'origin' in self._info:
				return self._info ['origin'].get_src_uri (
					self._info ['package_filename']
				)
			else:
				return "http://localhost/R-packages/" + \
					self._info ['package_filename']


		# fallback
		if do_fallback:
			return fallback_value

		elif key_low in VIRTUAL_KEYS ['ALWAYS_FALLBACK']:
			return None

		else:
			raise KeyError ( key )
	# --- end of get (...) ---

	def __getitem__ ( self, key ):
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

		self._writelock_acquire()

		for key, value in info.items():

			if key == 'filename':
				self._use_filename ( value )

			elif key in ( 'package_dir', 'dirpath', 'distdir' ):
				if value is not None:
					self ['distdir'] = value

			elif key == 'origin':
				self ['origin'] = value

			elif key == 'desc' or key == 'desc_data':
				self ['desc_data'] = value

			elif key == 'ebuild':
				self ['ebuild'] = value

			elif key == 'suggests':
				self ['has_suggests'] = value

			elif key == 'depres_results' or key == 'depres_result':
				self ['has_suggests'] = value [2]

			elif key == 'filepath':
				self._use_filepath ( value )

			else:
				LOGGER.warning ( "unknown info key %s!" % key )

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

		package_name, sepa, package_version = filename.partition (
			config.get ( 'R_PACKAGE.name_ver_separator', '_' )
		)

		if not sepa:
			# file name unexpected, tarball extraction will (probably) fail
			LOGGER.error    ( "unexpected file name '%s'." % filename )
			raise Exception ( "cannot use file '%s'." % filename )
			return

		version_str = PackageInfo.EBUILDVER_REGEX.sub ( '.', package_version )

		try:
			version = tuple ( int ( z ) for z in version_str.split ( '.' ) )
			self ['version'] = version
		except ValueError as ve:
			# version string is malformed
			# TODO: discard or continue with bad version?
			logging.error (
				"Cannot parse version string '%s' for '%s'"
					% ( _filename, version_str )
			)
			raise

		# using package name as name (unless modified later),
		#  using pkg_version for the ebuild version

		# removing illegal chars from the package_name
		ebuild_name = util.fix_ebuild_name ( package_name )

		if ebuild_name != package_name:
			self ['name'] = ebuild_name

		self ['ebuild_verstr']    = version_str

		# for DescriptionReader
		self ['package_name']     = package_name

		self ['package_filename'] = filename_with_ext
	# --- end of _use_filename (...) ---

	def _use_filepath ( self, _filepath ):
		"""auxiliary method for update(**kw)

		arguments:
		* _filepath --
		"""
		LOGGER.info (
			'Please note that _use_filepath is only meant for testing.'
		)
		filepath = os.path.abspath ( _filepath )
		self ['package_file'] = filepath
		self._use_filename ( os.path.basename ( filepath ) )
	# --- end of _use_filepath (...) ---

	def __str__ ( self ):
		return "<PackageInfo for %s>" % self.get (
			'package_file', fallback_value='[unknown file]', do_fallback=True
		)
	# --- end of __str__ (...) ---
