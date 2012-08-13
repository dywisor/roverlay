# R overlay -- remote, basicrepo
# -*- coding: utf-8 -*-
# Copyright (C) 2012 André Erdmann <dywi@mailerd.de>
# Distributed under the terms of the GNU General Public License;
# either version 2 of the License, or (at your option) any later version.

"""basic repo"""

__all__ = [ 'BasicRepo', ]

import os.path
import logging

from roverlay.packageinfo import PackageInfo

URI_SEPARATOR = '://'
DEFAULT_PROTOCOL = 'http'

LOCALREPO_SRC_URI = 'http://localhost/R-Packages'

SYNC_SUCCESS = 1
SYNC_FAIL    = 2
SYNC_DONE    = SYNC_SUCCESS | SYNC_FAIL
REPO_READY   = 4

def normalize_uri ( uri, protocol, force_protocol=False ):
	"""Returns an uri that is prefixed by its protocol ('http://', ...).
	Does nothing if protocol evaluates to False.

	arguments:
	* uri            --
	* protocol       -- e.g. 'http'
	* force_protocol -- replace an existing protocol
	"""

	if not protocol:
		return uri

	proto, sep, base_uri = uri.partition ( URI_SEPARATOR )
	if sep != URI_SEPARATOR:
		return URI_SEPARATOR.join ( ( protocol, uri ) )
	elif force_protocol:
		return URI_SEPARATOR.join ( ( protocol, base_uri ) )
	else:
		return uri
# --- end of normalize_uri (...) ---

class BasicRepo ( object ):
	"""
	This class represents a local repository - all packages are assumed
	to exist in its distfiles dir and no remote syncing will occur.
	It's the base class for remote repos.
	"""

	def __init__ ( self,
		name, distroot,
		directory=None, src_uri=None, is_remote=False, remote_uri=None
	):
		"""Initializes a LocalRepo.

		arguments:
		* name      --
		* directory -- distfiles dir, defaults to <DISTFILES root>/<name>
		* src_uri   -- SRC_URI, defaults to http://localhost/R-Packages/<name>
		"""
		self.name   = name
		self.logger = logging.getLogger (
			self.__class__.__name__ + ':' + self.name
		)

		if directory is None:
			# subdir repo names like CRAN/contrib are ok,
			#  but make sure to use the correct path separator
			self.distdir = \
				distroot + os.path.sep + self.name.replace ( '/', os.path.sep )

		else:
			self.distdir = directory

		if src_uri is None:
			self.src_uri = LOCALREPO_SRC_URI + '/' +  self.name
		elif len ( src_uri ) > 0 and src_uri [-1] == '/':
			self.src_uri = src_uri [:-1]
		else:
			self.src_uri = src_uri

		self.sync_status = 0

		if remote_uri is not None:
			self.is_remote  = True
			self.remote_uri = remote_uri
		else:
			self.is_remote  = is_remote
	# --- end of __init__ (...) ---

	def ready ( self ):
		"""Returns True if this repo is ready (for package scanning using
		scan_distdir).
		"""
		return bool ( self.sync_status & REPO_READY )
	# --- end of ready (...) ---

	def fail ( self ):
		"""Returns True if sync failed for this repo."""
		return bool ( self.sync_status & SYNC_FAIL )
	# --- end of fail (...) ---

	def offline ( self ):
		"""Returns True if this repo is offline (not synced)."""
		return 0 == self.sync_status & SYNC_DONE
	# --- end of offline (...) ---

	def _set_ready ( self, is_synced ):
		"""Sets the sync status of this repo to READY.

		arguments:
		* is_synced -- whether this repo has been synced
		"""
		if is_synced:
			self.sync_status = SYNC_SUCCESS | REPO_READY
		else:
			self.sync_status = REPO_READY
	# --- end of _set_ready (...) ---

	def _set_fail ( self ):
		"""Sets the sync status of this repo to FAIL."""
		self.sync_status = SYNC_FAIL
	# --- end of _set_fail (...) ---

	def __str__ ( self ):
		if hasattr ( self, 'remote_uri' ):
			return \
				'{cls} {name}: DISTDIR {distdir!r}, SRC_URI {src_uri!r}, '\
				'REMOTE_URI {remote_uri!r}.'.format (
					cls        = self.__class__.__name__,
					name       = self.name,
					distdir    = self.distdir,
					src_uri    = self.src_uri \
						if hasattr ( self, 'src_uri' ) else '[none]',
					remote_uri = self.remote_uri
				)
		else:
			return '{cls} {name}: DISTDIR {distdir!r}, SRC_URI {src_uri!r}.'.\
				format (
					cls     = self.__class__.__name__,
					name    = self.name,
					distdir = self.distdir,
					src_uri = self.src_uri \
						if hasattr ( self, 'src_uri' ) else '[none]'
				)
	# --- end of __str__ (...) ---

	def get_name ( self ):
		"""Returns the name of this repository."""
		return self.name
	# --- end of get_name (...) ---

	def get_distdir ( self ):
		"""Returns the distfiles directory of this repository."""
		return self.distdir
	# --- end of get_distdir (...) ---

	def get_remote_uri ( self ):
		"""Returns the remote uri of this RemoteRepo which used for syncing."""
		return self.remote_uri if hasattr ( self, 'remote_uri' ) else None
	# --- end of get_remote_uri (...) ---

	# get_remote(...) -> get_remote_uri(...)
	get_remote = get_remote_uri

	def get_src_uri ( self, package_file=None ):
		"""Returns the SRC_URI of this repository.

		arguments:
		* package_file -- if set and not None: returns a SRC_URI for this pkg
		"""
		if package_file is not None:
			return self.src_uri + '/' +  package_file
		else:
			return self.src_uri
	# --- end of get_src_uri (...) ---

	# get_src(...) -> get_src_uri(...)
	get_src = get_src_uri

	def exists ( self ):
		"""Returns True if this repo locally exists."""
		return os.path.isdir ( self.distdir )
	# --- end of exists (...) ---

	def sync ( self, sync_enabled=True ):
		"""Syncs this repo."""

		status = False
		if sync_enabled and hasattr ( self, '_dosync' ):
			status = self._dosync()

		elif hasattr ( self, '_nosync'):
			status = self._nosync()

		else:
			status = self.exists()

		if status:
			self._set_ready ( is_synced=sync_enabled )
		else:
			self._set_fail()

		return status
	# --- end of sync (...) ---

	def _package_nofail ( self, log_bad, filename, **data ):
		"""Tries to create a PackageInfo.
		Logs failure if log_bad is True.

		arguments:
		* log_bad  --
		* data     -- PackageInfo data

		returns: PackageInfo on success, else None.
		"""
		try:
			return PackageInfo ( filename=filename, **data )
		except ValueError as expected:
			if log_bad:
				#self.logger.exception ( expected )
				self.logger.info (
					"filtered {f!r}: bad package".format ( f=filename )
				)
			return None

	# --- end of _package_nofail (...) ---

	def scan_distdir ( self,
		is_package=None, log_filtered=False, log_bad=True
	):
		"""Generator that scans the local distfiles dir of this repo and
		yields PackageInfo instances.

		arguments:
		* is_package   -- function returning True if the given file is a package
		                   or None which means that all files are packages.
		                   Defaults to None.
		* log_filtered -- log files that did not pass is_package().
		                   Defaults to False; no effect if is_package is None.
		* log_bad      -- log files that failed the PackageInfo creation step
		                   Defaults to True.

		raises: AssertionError if is_package is neither None nor a callable.
		"""

		def package_nofail ( filename, distdir, src_uri_base ):
			return self._package_nofail (
				log_bad=log_bad,
				filename=filename,
				origin=self,
				distdir=distdir,
				src_uri_base=src_uri_base
			)
		# --- end of package_nofail (...) ---

		def get_distdir_and_srcuri_base ( dirpath ):
			if len ( dirpath ) > len ( self.distdir ):
				# package is in a subdirectory,
				#  get the relative path which is required for valid SRC_URIs
				if os.sep == '/':
					# a simple array slice does the job if os.sep is '/'
					subdir = dirpath [ len ( self.distdir ) + 1 : ]
				else:
					subdir = os.path.relpath ( dirpath, self.distdir ).replace (
						os.sep, '/'
					)

				return ( dirpath, self.src_uri + '/' + subdir )
			else:
				return ( None, None )
		# --- end of get_distdir_and_srcuri_base (...) ---

		if is_package is None:
			# unfiltered variant

			for dirpath, dirnames, filenames in os.walk ( self.distdir ):
				distdir, srcuri_base = get_distdir_and_srcuri_base ( dirpath )
				for filename in filenames:
					pkg = package_nofail ( filename, distdir, srcuri_base )
					if pkg is not None:
						yield pkg

		else:
			# filtered variant (adds an if is_package... before yield)
			for dirpath, dirnames, filenames in os.walk ( self.distdir ):
				distdir, srcuri_base = get_distdir_and_srcuri_base ( dirpath )

				for filename in filenames:
					if is_package ( os.path.join ( dirpath, filename ) ):
						pkg = package_nofail ( filename, distdir, srcuri_base )
						if pkg is not None:
							yield pkg
					elif log_filtered:
						self.logger.debug (
							"filtered {f!r}: not a package".format ( f=filename )
						)
	# --- end of scan_distdir (...) ---

# --- end of BasicRepo ---
