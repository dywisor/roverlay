import sys
import os.path
import logging

try:
	import configparser
except ImportError:
	# configparser is named ConfigParser in python2
	import ConfigParser as configparser


from roverlay import config

from roverlay.remote import basicrepo
from roverlay.remote import rsync
from roverlay.remote import websync

LOGGER = logging.getLogger ( 'repoloader' )

def read_repofile ( repo_file, distroot, lenient=False, force_distroot=False ):
	"""Reads a repo config file. Yields created repos.

	arguments:
	* repo_file     --
	* distroot      --
	* lenient       -- if set and True: do not fail if file is missing,
	                    allows reading of more than one file at once
	* force_distdir -- if set and True: use <DISTFILES.root>/<repo name>
	                                     as distdir for repos
	"""
	parser = configparser.SafeConfigParser ( allow_no_value=False )

	if lenient:
		parser.read ( repo_file )
	else:
		fh = None
		try:
			fh = open ( repo_file, 'r' )
			parser.readfp ( fh )
		finally:
			if fh: fh.close()

	for name in parser.sections():
		repo = None

		if sys.version_info >= ( 3, 2 ):
			get = lambda a, b=None : parser.get ( name, a, raw=True, fallback=b )
		else:
			get = lambda a, b=None: parser.get ( name, a, raw=True ) \
				if parser.has_option ( name, a ) else b

		repo_type = get ( 'type', 'rsync' ).lower()

		common_kwargs = dict (
			name      = get ( 'name', name ),
			directory = None if force_distroot else get ( 'directory' ),
			distroot  = distroot,
			src_uri   = get ( 'src_uri' )
		)



		if repo_type == 'local':
			repo = basicrepo.BasicRepo ( **common_kwargs )

		elif repo_type == 'rsync':
			extra_opts = get ( 'extra_rsync_opts' )
			if extra_opts:
				extra_opts = extra_opts.split ( ' ' )

			repo = rsync.RsyncRepo (
				rsync_uri  = get ( 'rsync_uri' ),
				extra_opts = extra_opts,
				recursive  = get ( 'recursive', False ) == 'yes',
				**common_kwargs
			)

		elif repo_type == 'websync_repo':
			repo = websync.WebsyncRepo (
				pkglist_file = get ( 'pkglist_file', 'PACKAGES' ),
				pkglist_uri  = get ( 'pkglist_uri' ),
				digest_type  = get ( 'digest_type' ) or get ( 'digest' ),
				**common_kwargs
			)

		elif repo_type in ( 'websync_pkglist', 'websync_package_list' ):
			repo = websync.WebsyncPackageList (
				pkglist_file = get ( 'pkglist_file' ) or get ( 'pkglist' ),
				#digest_type  = get ( 'digest_type' ) or get ( 'digest' ),
				**common_kwargs
			)

		else:
			LOGGER.error ( "Unknown repo type {} for {}!".format (
				repo_type, name
			) )


		if repo is not None:
			LOGGER.debug ( 'New entry, ' + str ( repo ) )
			yield repo

# --- end of read_repofile (...) ---
