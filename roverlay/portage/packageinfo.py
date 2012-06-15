# R Overlay -- package info class
# Copyright 2006-2012 Gentoo Foundation
# Distributed under the terms of the GNU General Public License v2

import re
import os.path
import logging
import threading

from roverlay import config, util

LOGGER = logging.getLogger ( 'PackageInfo' )

VIRTUAL_KEYS = dict (
	DISTDIR      = frozenset ( [ 'distdir', 'pkg_distdir' ] ),
	EBUILD_FILE  = frozenset ( [ 'ebuild_file', 'efile' ] ),
	HAS_SUGGESTS = frozenset ( [ 'has_suggests', 'has_rsuggests' ] ),
	SRC_URI      = frozenset ( [ 'src_uri', 'package_url', 'url' ] ),
)


class PackageInfo ( object ):
	"""PackageInfo offers easy, subscriptable (['sth']) access to package
	information, whether stored or calculated.
	"""

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
		key_low = key.lower()

		# 'virtual' keys - calculate result
		if key_low in VIRTUAL_KEYS ['DISTDIR']:
			if 'package_dir' in self._info:
				return self._info ['package_dir']

			elif 'origin' in self._info:
				return util.get_distdir ( self._info ['origin'] )

		elif key_low in VIRTUAL_KEYS ['EBUILD_FILE']:
			return os.path.join (
				config.get_or_fail ( [ 'OVERLAY', 'dir' ] ),
				config.get_or_fail ( [ 'OVERLAY', 'category' ] ),
				self ['ebuild_name'].partition ( '-' ) [0],
				self ['ebuild_name'] + ".ebuild"
			)

		elif key_low in VIRTUAL_KEYS ['HAS_SUGGESTS']:
			if key_low in self._info:
				return self._info [key_low]

			else:
				return False

		elif key_low in VIRTUAL_KEYS ['SRC_URI']:
			# comment from ebuildjob:
			## origin is todo (sync module knows the package origin)
			## could calculate SRC_URI in the eclass depending on origin
			# comment from ebuild:
			## calculate SRC_URI using self._data ['origin'],
			## either here or in eclass
			return "**packageinfo needs information from sync module!"

		# normal keys
		if key in self._info:
			return self._info [key]

		elif key_low in self._info:
			return self._info [key_low]

		elif do_fallback:
			return fallback_value
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

	def update ( self, **info ):
		"""Uses **info to update the package info data.

		arguments:
		* **info --

		raises: Exception when readonly
		"""
		if len ( info ) == 0 :
			# nothing to do
			return

		self._writelock_acquire()

		if 'filepath' in info:
			self._use_filepath ( info ['filepath'] )

		if 'ebuild' in info:
			self._use_ebuild ( info ['ebuild'] )

		self._update_lock.release()
	# --- end of update (**kw) ---

	def _use_filepath ( self, filepath ):
		"""auxiliary method for update(**kw)

		arguments:
		* filepath --
		"""

		package_file = os.path.basename ( filepath )

		# remove .tar.gz .tar.bz2 etc.
		filename = re.sub (
			config.get ( 'R_PACKAGE.suffix_regex' ) + '$',
			'',
			package_file
		)

		package_name, sepa, package_version = filename.partition (
			config.get ( 'R_PACKAGE.name_ver_separator', '_' )
		)

		if not sepa:
			# file name unexpected, tarball extraction will (probably) fail
			LOGGER.error    ( "unexpected file name '%s'." % filename )
			raise Exception ( "cannot use file '%s'." % filename )
			return


		self ['filepath']        = filepath
		self ['package_file']    = package_file
		self ['package_dir' ]    = os.path.dirname ( filepath )
		self ['filename']        = filename
		self ['package_name']    = package_name
		self ['package_version'] = package_version
	# --- end of _use_filepath (...) ---

	def _use_ebuild ( self, ebuild ):
		"""auxiliary method for update(**kw)

		arguments:
		* ebuild --
		"""
		self ['has_suggests'] =  ebuild.has_rsuggests
		# todo move Ebuild funcs to here
		self ['ebuild_dir']   = ebuild.suggest_dir_name()
		self ['ebuild_name']  = ebuild.suggest_name()
