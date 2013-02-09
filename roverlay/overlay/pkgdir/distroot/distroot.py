# R overlay -- overlay package, root of distdirs
# -*- coding: utf-8 -*-
# Copyright (C) 2013 André Erdmann <dywi@mailerd.de>
# Distributed under the terms of the GNU General Public License;
# either version 2 of the License, or (at your option) any later version.

__all__ = [
	'TemporaryDistroot', 'PersistentDistroot',
]

import atexit
import errno
import logging
import os
import shutil
import tempfile

import roverlay.overlay.pkgdir.distroot.distdir

class DistrootBase ( object ):
	"""Base class for distroots."""

	def __repr__ ( self ):
		return "{name}<root={root}>".format (
			name = self.__class__.__name__,
			root = self.get_root()
		)
	# --- end of __repr__ (...) ---

	def __str__ ( self ):
		return self.get_root()
	# --- end of __str__ (...) ---

	def __init__ ( self, root, flat ):
		"""DistrootBase constructor.

		arguments:
		* root -- root directory
		* flat -- whether to use a flat structure (all packages in a single
		           directory, True) or per-package sub directories (False)
		"""
		super ( DistrootBase, self ).__init__()
		self.logger = logging.getLogger ( self.__class__.__name__ )
		self._root  = root
		# or use hasattr ( self, '_default_distdir' )
		self._flat  = flat

		if flat:
			self._default_distdir = (
				roverlay.overlay.pkgdir.distroot.distdir.Distdir ( self )
			)

		if not os.path.isdir ( self._root ):
			os.makedirs ( self._root, 0o755 )

		self._prepare()
		atexit.register ( self._cleanup )
	# --- end of __init__ (...) ---

	def _add ( self, src, dest ):
		"""Adds src to the distroot.

		This method should be called by distdir objects.

		arguments:
		* src --
		* dest --
		"""
		# derived classes have to implement this
		raise NotImplementedError()
	# --- end of _add (...) ---

	def _add_symlink ( self, src, dest, filter_exceptions=False ):
		"""Adds src as symbolic link to the distroot.

		Returns True if the operation succeeded and False if an exception has
		been filtered out ("symlinks are not supported - try something else").
		Any other exception will be passed.

		arguments:
		* src --
		* dest --
		* filter_exceptions --
		"""

		if os.path.lexists ( dest ):
			# safe removal
			os.unlink ( dest )
		elif os.path.exists ( dest ):
			# unsafe removal (happens when switching from e.g. hardlinks)
			# FIXME log this
			os.unlink ( dest )

		if filter_exceptions:
			try:
				os.symlink ( src, dest )
			except OSError as err:
				if err.errno == errno.EPERM:
					# fs does not support symlinks
					return False
				else:
					raise
		else:
			os.symlink ( src, dest )

		return True
	# --- end of _add_symlink (...) ---

	def _add_hardlink ( self, src, dest, filter_exceptions=False ):
		"""Adds src as hard link to the distroot.

		Returns True if the operation succeeded and False if an exception has
		been filtered out ("hardlinks are not supported").
		Any other exception will be passed.

		arguments:
		* src --
		* dest --
		* filter_exceptions --
		"""
		self._try_remove ( dest )

		if filter_exceptions:
			try:
				os.link ( src, dest )
			except OSError as err:
				if err.errno == errno.EXDEV or err.errno == errno.EPERM:
					# cross-device link or filesystem does not support hard links
					return False
				else:
					raise
		else:
			os.link ( src, dest )

		return True
	# --- end of _add_hardlink (...) ---

	def _add_file ( self, src, dest, filter_exceptions=False ):
		"""Copies src to the distroot.

		Returns True if the operation succeeded and False if an exception has
		been filtered out ("copy is not supported").
		Any other exception will be passed.

		arguments:
		* src --
		* dest --
		* filter_exceptions --

		*** this function is DISABLED; it will always raise an Exception ***
		"""
		raise NotImplementedError ( "copy is disabled" )
#		# TODO: check whether copying is necessary
#		self._try_remove ( dest )
#		shutil.copyfile ( src, dest )
#		return True
	# --- end of _add_file (...) ---

	def _cleanup ( self ):
		"""Cleans up this distroot."""
		pass
	# --- end of _cleanup (...) ---

	def _prepare ( self ):
		"""Prepares the distroot."""
		pass
	# --- end of _prepare (...) ---

	def _remove_broken_symlinks ( self ):
		"""Recursively remove broken/dead symlinks."""
		def recursive_remove ( root, rmdir ):
			for item in os.listdir ( root ):
				fpath = root + os.sep + item

				if not os.path.exists ( fpath ):
					os.unlink ( fpath )

				elif os.path.isdir ( fpath ):
					recursive_remove ( fpath, True )
					if rmdir:
						try:
							os.rmdir ( fpath )
						except OSError:
							pass
		# --- end of recursive_remove (...) ---
		recursive_remove ( self.get_root(), False )
	# --- end of _remove_broken_symlinks (...) ---

	def _try_remove ( self, dest ):
		try:
			os.unlink ( dest )
		except OSError as e:
			if e.errno == errno.ENOENT:
				pass
			else:
				raise
	# --- end of _try_remove (...) ---

	def get_distdir ( self, ebuild_name ):
		"""Returns a distdir instance for given package.

		arguments:
		* package_name -- name of the ebuild (${PN}) for which a distdir will
		                  be created. A "flat" distdir will be returned if this
		                  is none.
		"""
		if self._flat:
			assert self._default_distdir._distroot is self
			return self._default_distdir
		elif ebuild_name is None:
			return roverlay.overlay.pkgdir.distroot.distdir.Distdir ( self )
		else:
			return roverlay.overlay.pkgdir.distroot.distdir.PackageDistdir (
				self, ebuild_name
			)
	# --- end of get_distdir (...) ---

	def get_root ( self ):
		return str ( self._root )
	# --- end of get_root (...) ---

# --- end of DistrootBase ---


class TemporaryDistroot ( DistrootBase ):

	def __init__ ( self ):
		# temporary distroots always use the non-flat distdir layout
		super ( TemporaryDistroot, self ).__init__ (
			root = tempfile.mkdtemp ( prefix='tmp_roverlay_distroot_' ),
			flat = False
		)
	# --- end of __init__ (...) ---

	def _add ( self, src, dest ):
		return self._add_symlink ( src, dest, filter_exceptions=False )
	# --- end of _add (...) ---

	def _cleanup ( self ):
		"""Cleans up the temporary distroot by simply wiping it."""
		shutil.rmtree ( self._root )
	# --- end of _cleanup (...) ---

# --- end of TemporaryDistroot ---


class PersistentDistroot ( DistrootBase ):

	USE_SYMLINK    = 1
	USE_HARDLINK   = 2
	USE_COPY       = 4

	USE_EVERYTHING = USE_SYMLINK | USE_HARDLINK | USE_COPY

	def __repr__ ( self ):
		return (
			'{name}<root={root}, strategy={s}, '
			'mode_mask={m_now}/{m_init}>'.format (
				name   = self.__class__.__name__,
				root   = self.get_root(),
				s      = self._strategy,
				m_now  = self._supported_modes,
				m_init = self._supported_modes_initial,
			)
		)
	# --- end of __repr__ (...) ---

	def __init__ ( self, root, flat, strategy ):
		"""Initializes a non-temporary distroot.

		arguments:
		* root     -- root directory
		* flat     -- whether to per-package subdirs (False) or not (True)
		* strategy -- the distroot 'strategy' that determines what mode (sym-
		              link, hardlink, copy) will be tried in which order
		              This has to be an iterable with valid items.
		"""
		super ( PersistentDistroot, self ).__init__ ( root=root, flat=flat )

		self._strategy = self._get_int_strategy ( strategy )

		# determine supported modes
		self._supported_modes = 0
		for s in self._strategy:
			self._supported_modes |= s
		# finally, restrict supported modes to what is available
		self._supported_modes &= self.USE_EVERYTHING

		self._supported_modes_initial = self._supported_modes

		# dict ( mode => function (arg^2, kwarg^1) )
		self._add_functions = {
			self.USE_SYMLINK  : self._add_symlink,
			self.USE_HARDLINK : self._add_hardlink,
			self.USE_COPY     : self._add_file,
		}
	# --- end of __init__ (...) ---

	def _add ( self, src, dest ):
		# race condition when accessing self._supported_modes
		#  * this can result in repeated log messages
		for mode in self._strategy:
			if self._supported_modes & mode:
				if self._add_functions [mode] (
					src, dest, filter_exceptions=True
				):
					return True
				else:
					self.logger.warning (
						"mode {} is not supported!".format ( mode )
					)
					# the _add function returned False, which means that the
					# operation is not supported
					# => remove mode from self._supported_modes
					self._supported_modes &= ~mode

					# any other exception is unexpected
					#  and will be passed to the caller

		else:
			raise Exception (
				"cannot add {src!r} to {root!r} as {destname!r}".format (
					src      = src,
					root     = self.get_root(),
					destname = os.path.basename ( dest )
				)
			)
	# --- end of _add (...) ---

	def _cleanup ( self ):
		if hasattr ( self, '_supported_modes_initial' ):
			if self._supported_modes_initial & self.USE_SYMLINK:
				self._remove_broken_symlinks()
	# --- end of _prepare (...) ---

	def _get_int_strategy ( self, strategy ):
		"""Converts the given strategy into its integer tuple representation.

		arguments:
		* strategy --
		"""
		def get_int ( item ):
			if hasattr ( item, '__int__' ):
				return int ( item )
			elif item == 'symlink':
				return self.USE_SYMLINK
			elif item == 'hardlink':
				return self.USE_HARDLINK
			elif item == 'copy':
				return  self.USE_COPY
			else:
				raise Exception (
					"unknown mode in strategy {!r}: {!r}".format ( strategy, item )
				)
		# --- end of get_int (...) ---

		#return [ get_int ( s ) for s in strategy ]
		return tuple ( get_int ( s ) for s in strategy )
	# --- end of _get_int_strategy (...) ---

# --- end of PersistentDistroot ---
