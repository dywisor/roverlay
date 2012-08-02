import re
import os
import sys

# py2 urllib2 vs py3 urllib.request
if sys.version_info >= ( 3, ):
	import urllib.request as _urllib
else:
	import urllib2 as _urllib

urlopen = _urllib.urlopen
del sys

from roverlay                  import digest, util
from roverlay.packageinfo      import PackageInfo
from roverlay.remote.basicrepo import BasicRepo

# FIXME: websync does not support package deletion

class WebsyncBase ( BasicRepo ):
	"""Provides functionality for retrieving R packages via http.
	Not meant for direct usage."""

	def __init__ ( self,
		name,
		distroot,
		src_uri,
		directory=None,
		digest_type=None
	):
		"""Initializes a WebsyncBase instance.

		arguments:
		* name        -- see BasicRepo
		* distroot    -- ^
		* src_uri     -- ^
		* directory   -- ^
		* digest_type -- if set and not None/"None":
		                  verify packages using the given digest type
		                  Supported digest types: 'md5'.
		"""
		super ( WebsyncBase, self ) . __init__ (
			name=name,
			distroot=distroot,
			src_uri=src_uri,
			remote_uri=src_uri,
			directory=directory
		)

		if digest_type is None:
			self._digest_type = None

		elif str ( digest_type ).lower() in ( 'none', 'disabled', 'off' ):
			self._digest_type = None

		elif digest.digest_supported ( digest_type ):
			# setting a digest_type (other than None) expects package_list
			# to be a 2-tuple <package_file, digest sum> list,
			# else a list of package_files is expected.
			self._digest_type = digest_type

		else:
			raise Exception (
				"Unknown/unsupported digest type {}!".format ( digest_type )
			)

		# download 8KiB per block
		self.transfer_blocksize = 8192
	# --- end of __init__ (...) ---

	def _fetch_package_list ( self ):
		"""This function returns a list of packages to download."""
		raise Exception ( "method stub" )
	# --- end of _fetch_package_list (...) ---

	def _get_package ( self, package_file, src_uri, expected_digest ):
		"""Gets a packages, i.e. downloads if it doesn't exist locally
		or fails verification (size, digest).

		arguments:
		* package_file    -- package file name
		* src_uri         -- uri for package_file
		* expected_digest -- expected digest for package_file or None (^=disable)
		"""
		distfile = self.distdir + os.sep + package_file
		webh     = urlopen ( src_uri )
		#web_info = webh.info()

		expected_filesize = int ( webh.info().get ( 'content-length', -1 ) )

		if os.access ( distfile, os.F_OK ):
			# package exists locally, verify it (size, digest)
			fetch_required = False
			localsize      = os.path.getsize ( distfile )

			if localsize != expected_filesize:
				# size mismatch
				self.logger.info (
					'size mismatch for {f!r}: expected {websize} bytes '
					'but got {localsize}!'.format (
						f         = package_file,
						websize   = expected_filesize,
						localsize = localsize
					)
				)
				fetch_required = True

			elif expected_digest is not None:
				our_digest = digest.dodigest_file ( distfile, self._digest_type )

				if our_digest != expected_digest:
					# digest mismatch
					self.logger.warning (
						'{dtype} mismatch for {f!r}: '
						'expected {theirs} but got {ours} - refetching.'.format (
							dtype  = self._digest_type,
							f      = distfile,
							theirs = expected_digest,
							ours   = our_digest
						)
					)
					fetch_required = True

		else:
			fetch_required = True

		if fetch_required:
			bytes_fetched = 0

			# FIXME: debug print (?)
			print (
				"Fetching {f} from {u} ...".format ( f=package_file, u=src_uri )
			)

			with open ( distfile, mode='wb' ) as fh:
				block = webh.read ( self.transfer_blocksize )
				while block:
					# write block to file
					fh.write ( block )
					# ? bytelen
					bytes_fetched += len ( block )

					# get the next block
					block = webh.read ( self.transfer_blocksize )
			# -- with

			if bytes_fetched == expected_filesize:
				if expected_digest is not None:
					our_digest = digest.dodigest_file ( distfile, self._digest_type )

					if our_digest != expected_digest:
						# fetched package's digest does not match the expected one,
						# refuse to use it
						self.logger.warning (
							'bad {dtype} digest for {f!r}, expected {theirs} but '
							'got {ours} - removing this package.'.format (
								dtype  = self._digest_type,
								f      = distfile,
								theirs = expected_digest,
								ours   = our_digest
							)
						)
						os.remove ( distfile )

						# package removed -> return success
						return True
					# -- if
				# -- if

			else:
				return False
		else:
			# FIXME: debug print
			print ( "Skipping fetch for {f!r}".format ( f=distfile ) )

		return self._package_synced ( package_file, distfile, src_uri )
	# --- end of get_package (...) ---

	def _package_synced ( self, package_filename, distfile, src_uri ):
		"""Called when a package has been synced (=exists locally when
		_get_package() is done).

		arguments:
		* package_filename --
		* distfile         --
		* src_uri          --
		"""
		return True
	# --- end of _package_synced (...) ---

	def _dosync ( self ):
		"""Syncs this repo."""
		package_list = self._fetch_package_list()

		# empty/unset package list
		if not package_list: return True

		util.dodir ( self.distdir )

		success = True

		if self._digest_type is not None:
			for package_file, expected_digest in package_list:
				src_uri  = self.get_src_uri ( package_file )

				if not self._get_package (
					package_file, src_uri, expected_digest
				):
					success = False
					break
		else:
			for package_file in package_list:
				src_uri  = self.get_src_uri ( package_file )

				if not self._get_package (
					package_file, src_uri, expected_digest=None
				):
					success = False
					break

		return success
	# --- end of _dosync (...) ---


class WebsyncRepo ( WebsyncBase ):
	"""Sync a http repo using its PACKAGES file."""
	# FIXME: hardcoded for md5

	def __init__ ( self,
		pkglist_uri=None,
		pkglist_file=None,
		*args,
		**kwargs
	):
		"""Initializes a WebsyncRepo instance.

		arguments:
		* pkglist_uri      -- if set and not None: uri of the package list file
		* pkglist_file     -- if set and not None: name of the package list file,
		                      this is used to calculate the pkglist_uri
		                      pkglist_uri = <src_uri>/<pkglist_file>
		* *args / **kwargs -- see WebsyncBase / BasicRepo

		pkglist file: this is a file with debian control file-like syntax
		              listing all packages.
		Example: http://www.omegahat.org/R/src/contrib/PACKAGES (2012-07-31)
		"""
		super ( WebsyncRepo, self ) . __init__ ( *args, **kwargs )

		if self._digest_type is None:
			self.FIELDREGEX = re.compile (
				'^\s*(?P<name>(package|version))[:]\s*(?P<value>.+)',
				re.IGNORECASE
			)
		else:
			# used to filter field names (package,version,md5sum)
			self.FIELDREGEX = re.compile (
				'^\s*(?P<name>(package|version|md5sum))[:]\s*(?P<value>.+)',
				re.IGNORECASE
			)

		self.pkglist_uri = pkglist_uri or self.get_src_uri ( pkglist_file )
		if not self.pkglist_uri:
			raise Exception ( "pkglist_uri is unset!" )
	# --- end of __init__ (...) ---

	def _fetch_package_list ( self ):
		"""Returns the list of packages to be downloaded.
		List format:
		* if digest verification is enabled:
		   List ::= [ ( package_file, digest ), ... ]
		* else
		   List ::= [ package_file, ... ]
		"""

		def generate_pkglist ( fh ):
			"""Generates the package list using the given file handle.

			arguments:
			* fh -- file handle to read from
			"""
			info = dict()

			max_info_len = 3 if self._digest_type is not None else 2

			for match in (
				filter (
					None,
					(
						self.FIELDREGEX.match (
							l if isinstance ( l, str ) else l.decode()
						)
						for l in fh.readlines()
					)
				)
			):
				name, value = match.group ( 'name', 'value' )
				info [name.lower()] = value

				if len ( info.keys() ) == max_info_len:

					pkgfile = '{name}_{version}.tar.gz'.format (
						name=info ['package'], version=info ['version']
					)

					if self._digest_type is not None:
						yield ( pkgfile, info ['md5sum'] )
						#yield ( pkgfile, ( 'md5', info ['md5sum'] ) )
					else:
						yield pkgfile

					info.clear()
		# --- end of generate_pkglist (...) ---

		package_list = ()
		try:
			webh = urlopen ( self.pkglist_uri )

			content_type = webh.info().get ( 'content-type', None )

			if content_type != 'text/plain':
				print (
					"content type {!r} is not supported!".format ( content_type )
				)
			else:
				package_list = tuple ( generate_pkglist ( webh ) )

			webh.close()

		finally:
			if 'webh' in locals() and webh: webh.close()

		return package_list
	# --- end fetch_pkglist (...) ---

class WebsyncPackageList ( WebsyncBase ):
	"""Sync packages from multiple remotes via http. Packages uris are read
	from a file."""

	def __init__ ( self, pkglist_file, *args, **kwargs ):
		"""Initializes a WebsyncPackageList instance.

		arguments:
		* pkglist_file     -- path to the package list file that lists
		                      one package http uri per line
		* *args / **kwargs -- see WebsyncBase, BasicRepo
		"""
		super ( WebsyncPackageList, self ) . __init__ ( *args, **kwargs )

		self._pkglist_file = os.path.abspath ( pkglist_file )

		del self.src_uri

		self._synced_packages = list()

	# --- end of __init__ (...) ---

	def _fetch_package_list ( self ):
		"""Returns the package list.
		Format:
		pkglist ::= [ ( package_file, src_uri ), ... ]
		"""
		pkglist = list()
		with open ( self._pkglist_file, mode='r' ) as fh:
			for line in fh.readlines():
				src_uri = line.strip()
				if src_uri:
					pkglist.append ( (
						src_uri.rpartition ( '/' ) [-1],
						src_uri
					) )

		return pkglist
	# --- end of _fetch_package_list (...) ---

	def _package_synced ( self, package_filename, distfile, src_uri ):
		self._synced_packages.append (
			( package_filename, src_uri )
		)
		return True
	# --- end of _package_synced (...) ---

	def scan_distdir ( self, log_bad=True, **kwargs_ignored ):
		for package_filename, src_uri in self._synced_packages:
			pkg = self._package_nofail (
				log_bad,
				filename = package_filename,
				origin   = self,
				src_uri  = src_uri
			)
			if pkg is not None:
				yield pkg
	# --- end of scan_distdir (...) ---

	def _nosync ( self ):
		"""nosync - report existing packages"""
		for package_file, src_uri in self._fetch_package_list():
			distfile = self.distdir + os.sep + package_file
			if os.access ( distfile, os.F_OK ):
				self._package_synced ( package_file, distfile, src_uri )

		return True
	# --- end of _nosync (...) ---

	def _dosync ( self ):
		"""Sync packages."""
		package_list = self._fetch_package_list()

		# empty/unset package list
		if not package_list: return True

		util.dodir ( self.distdir )

		success = True

		for package_file, src_uri in package_list:
			if not self._get_package (
				package_file, src_uri, expected_digest=None
			):
				success = False
				break

		return success
	# --- end of _dosync (...) ---