import os
import sys
import subprocess

from roverlay import config, util

#from roverlay.remote.basicrepo import LocalRepo, RemoteRepo
from roverlay.remote.basicrepo import RemoteRepo

RSYNC_ENV = util.keepenv (
	'PATH',
	'USER',
	'LOGNAME',
	'RSYNC_PROXY',
	'RSYNC_PASSWORD',
)

# TODO:
# either reraise an KeyboardInterrupt while running rsync (which stops script
# execution unless the interrupt is catched elsewhere) or just set a
# non-zero return code (-> 'repo cannot be used')
RERAISE_INTERRUPT = False

# --recursive is not in the default opts, subdirs in CRAN/contrib are
# either R releases (2.xx.x[-patches]) or the package archive
DEFAULT_RSYNC_OPTS =  (
	'--links',                  # copy symlinks as symlinks,
	'--safe-links',             #  but ignore links outside of tree
	'--times',                  #
	'--compress',               # FIXME: add lzo if necessary
	'--dirs',                   #
	'--prune-empty-dirs',       #
	'--force',                  # allow deletion of non-empty dirs
	'--delete',                 #
	'--human-readable',         #
	'--stats',                  #
	'--chmod=ugo=r,u+w,Dugo+x', # 0755 for transferred dirs, 0644 for files
)

class RsyncRepo ( RemoteRepo ):

	def __init__ (
		self, name,
		directory=None, src_uri=None, rsync_uri=None, base_uri=None,
		recursive=False, extra_opts=None
	):
		"""Initializes an RsyncRepo.

		arguments:
		* name       --
		* directory  --
		* src_uri    --
		* rsync_uri  --
		* base_uri   --
		* recursive  -- if '--recursive' should be included in the rsync opts
		* extra_opts -- extra opts for rsync (either None or a tuple/list/..)
		"""
		# super's init: name, remote protocol, directory_kw, **uri_kw
		#  using '' as remote protocol which leaves uris unchanged when
		#   normalizing them for rsync usage
		super ( RsyncRepo, self ) . __init__ (
			name, '', directory=directory,
			src_uri=src_uri, remote_uri=rsync_uri, base_uri=base_uri
		)

		# syncing directories, not files - always appending a slash at the end
		# of remote
		if self.remote_uri [-1] != '/':
			self.remote_uri = self.remote_uri + '/'

		if recursive:
			self.extra_opts = [ '--recursive' ]
			if extra_opts:
				self.extra_opts.extend ( extra_opts )
		else:
			self.extra_opts = extra_opts

		self.sync_protocol = 'rsync'
	# --- end of __init__ (...) ---

	def _rsync_argv ( self ):
		"""Returns an rsync command used for syncing."""
		argv = [ 'rsync' ]

		argv.extend ( DEFAULT_RSYNC_OPTS )

		max_bw = config.get ( 'RSYNC_BWLIMIT', None )
		if max_bw is not None:
			argv.append ( '--bwlimit=%i' % max_bw )

		if self.extra_opts:
			argv.extend ( self.extra_opts )

		argv.extend ( ( self.remote_uri, self.distdir ) )

		# removing emty args from argv
		return tuple ( filter ( None, argv ) )

	# --- end of _rsync_argv (...) ---

	def _dosync ( self ):
		"""Syncs this repo. Returns True if sync succeeded, else False.
		All exceptions(?) are catched and interpreted as sync failure.
		"""

		retcode = '<undef>'

		try:

			rsync_cmd = self._rsync_argv()

			util.dodir ( self.distdir, mkdir_p=True )

			self.logger.debug ( 'running rsync cmd: ' + ' '.join ( rsync_cmd ) )


			proc = subprocess.Popen (
				rsync_cmd,
				stdin=None, stdout=None, stderr=None,
				env=RSYNC_ENV
			)

			if proc.communicate() != ( None, None ):
				raise AssertionError ( "expected None,None from communicate!" )

			if proc.returncode == 0:
				self._set_ready ( is_synced=True )
				return True

			retcode = proc.returncode

		except KeyboardInterrupt:
			sys.stderr.write (
				"\nKeyboard interrupt - waiting for rsync to exit...\n"
			)
			if 'proc' in locals():
				proc.communicate()
				retcode = proc.returncode
			else:
				retcode = 130

			if RERAISE_INTERRUPT:
				raise

		except Exception as e:
			# catch exceptions, log them and return False
			## TODO: which exceptions to catch||pass?
			self.logger.exception ( e )

		self.logger.error (
			'Repo %s cannot be used for ebuild creation due to errors '
			'while running rsync (return code was %s).' % ( self.name, retcode )
		)
		self._set_fail()
		return False
	# --- end of _dosync (...) ---

	def __str__ ( self ):
		return "rsync repo '%s': DISTDIR '%s', SRC_URI '%s', RSYNC_URI '%s'" \
			% ( self.name, self.distdir, self.src_uri, self.remote_uri )
	# --- end of __str__ (...) ---
