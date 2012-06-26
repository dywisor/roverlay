import os
import sys
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

class RsyncJob ( object ):
	def __init__ (
		self, remote=None, distdir=None, run_now=True,
		extra_opts=None, recursive=False
	):
		self.distdir = distdir

		# syncing directories, not files - always appending a slash at the end
		# of remote
		if remote [-1] != '/':
			self.remote = remote + '/'
		else:
			self.remote = remote

		if recursive:
			self.extra_opts = [ '--recursive' ]
			if extra_opts:
				self.extra_opts.extend ( extra_opts )
		else:
			self.extra_opts = extra_opts


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

		if self.extra_opts:
			argv.extend ( self.extra_opts )

		argv.extend ( ( self.remote, self.distdir ) )


		# removing emty args from argv
		return tuple ( filter ( None, argv ) )
	# --- end of _rsync_argv (...) ---

	def run ( self ):

		rsync_cmd = self._rsync_argv()
		print ( ' '.join ( rsync_cmd ) )

		os.makedirs ( self.distdir, exist_ok=True )

		# TODO pipe/log/.., running this in blocking mode until implemented
		try:
			proc = subprocess.Popen (
				rsync_cmd,
				stdin=None, stdout=None, stderr=None,
				env=RSYNC_ENV
			)

			if proc.communicate() != ( None, None ):
				raise AssertionError ( "expected None,None from communicate!" )

			self.returncode = proc.returncode

		except KeyboardInterrupt:
			sys.stderr.write (
				"\nKeyboard interrupt - waiting for rsync to exit...\n"
			)
			if 'proc' in locals():
				proc.communicate()
				self.returncode = proc.returncode
			else:
				self.returncode = 130

			if RERAISE_INTERRUPT:
				raise
	# --- end of start (...) ---
