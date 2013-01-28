# R overlay -- overlay package, symlink distroot
# -*- coding: utf-8 -*-
# Copyright (C) 2013 André Erdmann <dywi@mailerd.de>
# Distributed under the terms of the GNU General Public License;
# either version 2 of the License, or (at your option) any later version.

__all__ = [ 'SymlinkDistroot', 'ThreadsafeSymlinkDistroot' ]

import os
import atexit
import shutil
import tempfile
import threading
import logging

import roverlay.config

import roverlay.overlay.pkgdir.symlink.distdir

class _SymlinkDistrootBase ( object ):

	_instance_lock = threading.Lock()
	__instance     = None

	@classmethod
	def get_configured ( cls ):
		"""Returns the static SymlinkDistroot instance."""
		if cls.__instance is None:
			with cls._instance_lock:
				if cls.__instance is None:
					cls.__instance = cls (
						root = roverlay.config.get (
							'OVERLAY.SYMLINK_DISTROOT.root', ""
						),
						is_tmpdir = roverlay.config.get_or_fail (
							'OVERLAY.SYMLINK_DISTROOT.tmp'
						),
					)
		return cls.__instance
	# --- end of get_configured (...) ---

	def __repr__ ( self ):
		return "{}<root={}, tmpdir={}>".format (
			self.__class__.__name__, self._root, self._is_tmpdir
		)
	# --- end of __repr__ (...) ---

	def __str__ ( self ):
		return str ( self._root )
	# --- end of __str__ (...) ---

	def __init__ ( self, root, is_tmpdir ):
		"""Initializes a _SymlinkDistrootBase instance.

		arguments:
		* root      -- root directory where per-package SymlinkDistdirs will
		               be created. An empty value is only valid if is_tmpdir
		               evaluates to True.
		* is_tmpdir -- whether this SymlinkDistroot is a temporary directory
		               or not. A temporary directory will be wiped at exit,
		               while a non-temporary one will only be cleaned up.

		tempfile.mktempd() will be used as directory if root is empty
		and is_tmpdir is true.

		Raises: ConfigError if root is not set and is_tmpdir evaluates to False.
		"""
		super ( _SymlinkDistrootBase, self ).__init__()

		self._root      = root
		self._is_tmpdir = bool ( is_tmpdir )

		if not self._root:
			if self._is_tmpdir:
				self._root = tempfile.mkdtemp ( prefix='tmp_roverlay_sym' )
			else:
				raise roverlay.config.ConfigError (
					"OVERLAY.symlink_distroot: invalid value."
				)
		elif not os.path.isdir ( self._root ):
			os.makedirs ( self._root, 0o755 )

		self._prepare()

		atexit.register ( self._destroy if self._is_tmpdir else self._cleanup )
	# --- end of __init__ (...) ---

	def _cleanup ( self ):
		"""Cleans up a SymlinkDistroot."""
		# derived classes can implement this to define actions for non-temporary
		# SymlinkDistroots  that will be performed at ext.
		pass
	# --- end of _cleanup (...) ---

	def _destroy ( self, force=False ):
		"""Destroys a SymlinkDistroot.

		arguments:
		* force -- force destruction even if this distroot is not temporary
		"""
		if force or self._is_tmpdir:
			shutil.rmtree ( self._root )
	# --- end of _destroy (...) ---

	def _get ( self, package_name ):
		"""Returns a new SymlinkDistdir instance for given package.

		arguments:
		* package_name -- will be used as subdirectory name and must not
		                  contain any os.sep chars (typically "/")
		"""
		assert os.sep not in package_name
		return roverlay.overlay.pkgdir.symlink.distdir.SymlinkDistdir (
			self._root + os.sep + package_name
		)
	# --- end of get (...) ---

	def _prepare ( self ):
		"""Prepares the SymlinkDistroot. Called for both temporary and
		persistent distroots.

		The default actions is to remove broken symlinks.
		"""
		if not self._is_tmpdir:
			self.remove_broken_symlinks ( unsafe_assumptions=True )
	# --- end of _prepare (...) ---

	def get ( self, package_name ):
		"""Returns a SymlinkDistdir for the given package.

		arguments:
		* package_name

		Has to be implemented by derived classes.
		"""
		raise NotImplementedError()
	# --- end of get (...) ---

	def remove_broken_symlinks ( self, unsafe_assumptions=False ):
		"""Recursively remove broken/dead symlinks.

		arguments:
		* unsafe_assumptions -- use (potentially) faster but less safe code
		"""
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

		if unsafe_assumptions:
			# completely "unroll" the recursion using the following assumptions:
			# * self._root contains directories only
			# * maximum recursion depth is 1 (no nested subdir structure)

			for d_item in os.listdir ( self._root ):
				d_path = self._root + os.sep + d_item

				for l_item in os.listdir ( d_path ):
					l_path = self._root + os.sep + l_item
					if not os.path.exists ( l_path ):
						os.unlink ( l_path )

				try:
					os.rmdir ( dpath )
				except OSError:
					pass
		else:
			recursive_remove ( self._root, False )

	# --- end of remove_broken_symlinks (...) ---

# --- end of _SymlinkDistrootBase ---

class SymlinkDistroot ( _SymlinkDistrootBase ):
	"""A symlink distroot that uses a dict to remember
	per-package SymlinkDistdirs.
	"""

	# _not_ threadsafe, but get() is expected to be called
	#  within a (per-package_name) threadsafe context

	def __init__ ( self, *args, **kwargs ):
		"""see _SymlinkDistrootBase.__init__()"""
		super ( SymlinkDistroot, self ).__init__ ( *args, **kwargs )
		self._subdirs = dict()
	# --- end of __init__ (...) ---

	def get ( self, package_name ):
		"""Returns a SymlinkDistdir for the given package.

		arguments:
		* package_name --
		"""
		try:
			return self._subdirs [package_name]
		except KeyError:
			self._subdirs [package_name] = self._get ( package_name )
			return self._subdirs [package_name]
	# --- end of get (...) ---

# --- end of SymlinkDistroot ---

class ThreadsafeSymlinkDistroot ( SymlinkDistroot ):
	"""Like SymlinkDistroot, but locks while creating SymlinkDistdirs."""

	# will be removed if SymlinkDistroot is sufficient.

	def __init__ ( self, *args, **kwargs ):
		super ( ThreadsafeSymlinkDistroot, self ).__init__ ( *args, **kwargs )
		self._lock = threading.Lock()
	# --- end of __init__ (...) ---

	def get ( self, package_name ):
		try:
			return self._subdirs [package_name]
		except KeyError:
			with self._lock:
				if package_name not in self._subdirs:
					self._subdirs [package_name] = self._get ( package_name )
			return self._subdirs [package_name]
	# --- end of get (...) ---

# --- end of ThreadsafeSymlinkDistroot ---
