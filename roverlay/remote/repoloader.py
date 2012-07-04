import sys
import os.path
import logging

try:
	import configparser
except ImportError:
	# configparser is named ConfigParser in python2
	import ConfigParser as configparser


from roverlay import config

from roverlay.remote.basicrepo import LocalRepo
from roverlay.remote.rsync     import RsyncRepo

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

		if sys.version_info < ( 3, 2 ):
			# FIXME replace this and use more accurate version condition
			get = lambda a, b=None: parser.get ( name, a, raw=True ) \
				if parser.has_option ( name, a ) else b
		else:
			get = lambda a, b=None : parser.get ( name, a, raw=True, fallback=b )

		repo_type = get ( 'type', 'rsync' ).lower()

		repo_name = get ( 'name', name )

		repo_distdir = None if force_distroot else get ( 'directory' )


		if repo_type == 'local':
			repo = LocalRepo (
				name      = repo_name,
				distroot  = distroot,
				directory = repo_distdir,
				src_uri   = get ( 'src_uri' )
			)
		elif repo_type == 'rsync':
			extra_opts = get ( 'extra_rsync_opts' )
			if extra_opts:
				extra_opts = extra_opts.split ( ' ' )

			repo = RsyncRepo (
				name       = repo_name,
				distroot   = distroot,
				directory  = repo_distdir,
				src_uri    = get ( 'src_uri' ),
				rsync_uri  = get ( 'rsync_uri' ),
				base_uri   = get ( 'base_uri' ),
				extra_opts = extra_opts,
				recursive  = get ( 'recursive', False ) == 'yes',
			)
		else:
			LOGGER.error ( "Unknown repo type %s for %s" % ( repo_type, name ) )


		if repo is not None:
			LOGGER.debug ( 'New entry, ' + str ( repo ) )
			yield repo

# --- end of read_repofile (...) ---
