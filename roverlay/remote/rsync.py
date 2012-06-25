import os
import subprocess

from roverlay      import config
from roverlay.util import keepenv


RSYNC_ENV = keepenv (
	'PATH',
	'USER',
	'LOGNAME',
	'RSYNC_PROXY',
	'RSYNC_PASSWORD',
)


# --recursive is not in the default opts, subdirs in CRAN/contrib are
# either R release (2.xx.x[-patches] or the package archive)
DEFAULT_RSYNC_OPTS =  (
	'--links',                  # copy symlinks as symlinks,
	'--safe-links',             #  but ignore links outside of tree
	'--times',                  #
	'--compress',               # FIXME: add lzo if necessary
	'--delete',                 #
	'--force',                  # allow deletion of non-empty dirs
	'--human-readable',         #
	'--stats',                  #
	'--chmod=ugo=r,u+w,Dugo+x', # 0755 for transferred dirs, 0644 for files
)

class RsyncJob ( object ):
	def __init__ (
		self, remote=None, distdir=None, run_now=True, extra_opts=None
	):
		self.remote     = remote
		self.distdir   = distdir
		self.extra_opts = None

		if run_now: self.run()
	# --- end of __init__ (...) ---

	def _rsync_argv ( self ):
		if self.remote is None or self.distdir is None:
			raise Exception ( "None in (remote,distdir)." )

		argv = [ 'rsync' ]

		argv.extend ( DEFAULT_RSYNC_OPTS )

		max_bw = config.get ( 'RSYNC_BWLIMIT', None )
		if max_bw is not None:
			argv.append ( '--bwlimit=%i' % max_bw )

		if self.extra_opts is not None:
			if isinstance ( self.extra_opts, str ) or \
				not hasattr ( self.extra_opts, '__iter__' )\
			:
				argv.append ( self.extra_opts )
			else:
				argv.extend ( self.extra_opts )

		argv.extend ( ( self.remote, self.distdir ) )

		return argv
	# --- end of _rsync_argv (...) ---

	def run ( self ):

		rsync_cmd = self._rsync_argv()

		os.makedirs ( self.distdir, exist_ok=True )

		# TODO pipe/log/.., running this in blocking mode until implemented

		proc = subprocess.Popen (
			rsync_cmd,
			stdin=None, stdout=None, stderr=None,
			env=RSYNC_ENV
		)

		if proc.communicate() != ( None, None ):
			raise AssertionError ( "expected None,None from communicate!" )

		self.returncode = proc.returncode

	# --- end of start (...) ---
