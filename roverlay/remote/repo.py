
import logging

#from roverlay.remote.basicrepo import LocalRepo, RemoteRepo
from roverlay.remote.basicrepo import RemoteRepo

from roverlay.remote.rsync import RsyncJob

class RsyncRepo ( RemoteRepo ):

	def __init__ (
		self, name,
		directory=None, src_uri=None, rsync_uri=None, base_uri=None,
		extra_rsync_opts=None
	):
		# super's init: name, remote protocol, directory_kw, **uri_kw
		#  using '' as remote protocol which leaves uris unchanged when
		#   normalizing them for rsync usage
		super ( RsyncRepo, self ) . __init__ (
			name, '', directory=directory,
			src_uri=src_uri, remote_uri=rsync_uri, base_uri=base_uri
		)
		self.extra_rsync_opts = extra_rsync_opts
	# --- end of __init__ (...) ---


	def sync ( self ):
		retcode = None
		try:
			job = RsyncJob (
				remote=self.remote_uri, distdir=self.distdir,
				run_now=True,
				extra_opts=self.extra_rsync_opts
			)
			if job.returncode == 0: return True

			retcode = job.returncode
		except Exception as e:
			# catch exceptions, log them and return False
			## TODO: which exceptions to catch||pass?
			logging.exception ( e )
			retcode = '<undef>'


		logging.error (
			'Repo %s cannot be used for ebuild creation due to errors '
			'while running rsync (return code was %s).' % ( self.name, retcode )
		)
		return False
	# --- end of sync (...) ---

	def __str__ ( self ):
		return "rsync repo '%s': DISTDIR '%s', SRC_URI '%s', RSYNC_URI '%s'" \
			% ( self.name, self.distdir, self.src_uri, self.remote_uri )
