import sys
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

def read_repofile ( repo_file, lenient=False ):
	"""Reads a repo config file. Returns the list of created repos.

	arguments:
	* repo_file --
	* lenient   -- if True: do not fail if file is missing, allows reading
	                        of more than one file at once
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

	repos = list()

	for name in parser.sections():

		if sys.version_info < ( 3, 2 ):
			# FIXME replace this and use more accurate version condition
			get = lambda a, b=None: parser.get ( name, a, raw=True ) \
				if parser.has_option ( name, a ) else b
		else:
			get = lambda a, b=None : parser.get ( name, a, raw=True, fallback=b )

		repo_type = get ( 'type', 'rsync' ).lower()

		if repo_type == 'local':
			repo = LocalRepo (
				name      = get ( 'name', name ),
				directory = get ( 'directory' ),
				src_uri   = get ( 'src_uri' )
			)
		elif repo_type == 'rsync':
			extra_opts = get ( 'extra_rsync_opts' )
			if extra_opts:
				extra_opts = extra_opts.split ( ' ' )

			repo = RsyncRepo (
				name             = get ( 'name', name ),
				directory        = get ( 'directory' ),
				src_uri          = get ( 'src_uri' ),
				rsync_uri        = get ( 'rsync_uri' ),
				base_uri         = get ( 'base_uri' ),
				extra_opts       = extra_opts,
				recursive        = get ( 'recursive', False ) == 'yes',
			)
		else:
			LOGGER.error ( "Unknown repo type %s for %s" % ( repo_type, name ) )
			continue

		LOGGER.debug ( 'New entry, ' + str ( repo ) )

		repos.append ( repo )
		repo = None


	return repos
# --- end of read_repofile (...) ---
