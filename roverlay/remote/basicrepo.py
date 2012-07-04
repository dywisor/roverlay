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

class LocalRepo ( object ):
	"""
	This class represents a local repository - all packages are assumed
	to exist in its distfiles dir and no remote syncing will occur.
	It's the base class for remote repos.
	"""

	def __init__ ( self, name, distroot, directory=None, src_uri=None ):
		"""Initializes a LocalRepo.

		arguments:
		* name      --
		* directory -- distfiles dir, defaults to <DISTFILES root>/<name>
		* src_uri   -- SRC_URI, defaults to http://localhost/R-Packages/<name>
		"""
		self.name = name

		self.logger = logging.getLogger (
			self.__class__.__name__ + ':' + self.name
		)

		if directory is None:
			self.distdir = os.path.join (
				distroot,
				# subdir repo names like CRAN/contrib are ok,
				#  but make sure to use the correct path separator
				self.name.replace ( '/', os.path.sep ),
			)
		else:
			self.distdir = directory

		if src_uri is None:
			self.src_uri = '/'.join ( ( LOCALREPO_SRC_URI, self.name ) )
		else:
			self.src_uri = src_uri

		self.sync_status = 0

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
		return "repo '%s': DISTDIR '%s', SRC_URI '%s'" % (
			self.name, self.distdir, self.src_uri
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

	def get_src_uri ( self, package_file=None ):
		"""Returns the SRC_URI of this repository.

		arguments:
		* package_file -- if set and not None: returns a SRC_URI for this pkg
		"""
		if package_file is None:
			return self.src_uri
		else:
			return '/'.join ( ( self.src_uri, package_file ) )
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

		def package_nofail ( filename, distdir ):
			"""Tries to create a PackageInfo.
			Logs failure if log_bad is True.

			arguments:
			* filename -- name of the package file (including .tar* suffix)
			* distdir  -- filename's directory

			returns: PackageInfo on success, else None.
			"""
			try:
				return PackageInfo (
					filename=filename, origin=self, distdir=distdir
				)
			except ( ValueError, ) as expected:
				if log_bad:
					#self.logger.exception ( expected )
					self.logger.info (
						"filtered %r: bad package" % filename
					)
				return None

		# --- end of package_nofail (...) ---

		if is_package is None:
			# unfiltered variant

			for dirpath, dirnames, filenames in os.walk ( self.distdir ):
				distdir = dirpath if dirpath != self.distdir else None

				for filename in filenames:
					pkg = package_nofail ( filename, distdir )
					if pkg is not None:
						yield pkg

		elif hasattr ( is_package, '__call__' ):
			# filtered variant (adds an if is_package... before yield)
			for dirpath, dirnames, filenames in os.walk ( self.distdir ):
				distdir = dirpath if dirpath != self.distdir else None

				for filename in filenames:
					if is_package ( os.path.join ( dirpath, filename ) ):
						pkg = package_nofail ( filename, distdir )
						if pkg is not None:
							yield pkg
					elif log_filtered:
						self.logger.debug (
							"filtered %r: not a package" % filename
						)


		else:
			# faulty variant, raises Exception
			raise AssertionError (
				"is_package should either be None or a function."
			)
			#yield None

	# --- end of scan_distdir (...) ---

# --- end of LocalRepo ---


class RemoteRepo ( LocalRepo ):
	"""A template for remote repositories."""

	def __init__ (
		self, name, sync_proto,
		directory=None,
		src_uri=None, remote_uri=None, base_uri=None
	):
		"""Initializes a RemoteRepo.
		Mainly consists of URI calculation that derived classes may find useful.

		arguments:
		* name       --
		* sync_proto -- protocol used for syncing (e.g. 'rsync')
		* directory  --
		* src_uri    -- src uri, if set, else calculated using base/remote uri,
		                 the leading <proto>:// can be left out in which case
		                 http is assumed
		* remote_uri -- uri used for syncing, if set, else calculated using
		                 base/src uri, the leading <proto>:// can be left out
		* base_uri   -- used to calculate remote/src uri,
		                 example: localhost/R-packages/something

		keyword condition:
		* | { x : x in union(src,remote,base) and x not None } | >= 1
		 ^= at least one out of src/remote/base uri is not None
		"""
		super ( RemoteRepo, self ) . __init__ ( name, directory, src_uri='' )

		self.sync_proto = sync_proto

		# detemerine uris
		if src_uri is None and remote_uri is None:
			if base_uri is None:
				# keyword condition not met
				raise Exception ( "Bad initialization of RemoteRepo!" )

			else:
				# using base_uri for src,remote
				self.src_uri = URI_SEPARATOR.join (
					( DEFAULT_PROTOCOL, base_uri )
				)

				self.remote_uri = URI_SEPARATOR.join (
					( sync_proto, base_uri )
				)

		elif src_uri is None:
			# remote_uri is not None
			self.remote_uri = normalize_uri ( remote_uri, self.sync_proto )

			if base_uri is not None:
				# using base_uri for src_uri
				self.src_uri = URI_SEPARATOR.join (
					( DEFAULT_PROTOCOL, base_uri )
				)
			else:
				# using remote_uri for src_uri
				self.src_uri = normalize_uri (
					self.remote_uri, DEFAULT_PROTOCOL, force_protocol=True
				)

		elif remote_uri is None:
			# src_uri is not None
			self.src_uri = normalize_uri ( src_uri, DEFAULT_PROTOCOL )

			if base_uri is not None:
				# using base_uri for remote_uri
				self.remote_uri = URI_SEPARATOR.join (
					( self.sync_proto, base_uri )
				)
			else:
				# using src_uri for remote_uri
				self.remote_uri = normalize_uri (
					self.src_uri, self.sync_proto, force_protocol=True
				)
		else:
			# remote and src not None
			self.remote_uri = normalize_uri ( remote_uri, self.sync_proto )
			self.src_uri    = normalize_uri ( src_uri, DEFAULT_PROTOCOL )

	# --- end of __init__ (...) ---

	def get_remote_uri ( self ):
		"""Returns the remote uri of this RemoteRepo which used for syncing."""
		return self.remote_uri
	# --- end of get_remote_uri (...) ---

	# get_remote(...) -> get_remote_uri(...)
	get_remote = get_remote_uri

	def _dosync ( self ):
		"""Gets packages from remote(s) and returns True if the repo is ready
		for overlay creation, else False.

		Derived classes have to implement this method.
		"""
		raise Exception ( "RemoteRepo does not implement sync()." )
	# --- end of _dosync (...) ---

	def __str__ ( self ):
		return "repo '%s': DISTDIR '%s', SRC_URI '%s', REMOTE_URI '%s'" % (
			self.name, self.distdir, self.src_uri, self.remote_uri
		)
	# --- end of __str__ (...) ---

# --- end of RemoteRepo ---

