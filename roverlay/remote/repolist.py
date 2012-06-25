
from roverlay import config

from roverlay.remote.repoloader import read_repofile

class RepoList ( object ):

	def __init__ ( self ):
		self.repos = list()
		self.sync_enabled = True
		self.use_broken_repos = False

	def sort ( self ):
		raise Exception ( "method stub." )

	def load_file ( self, _file ):
		new_repos = read_repofile ( _file )
		if new_repos:
			self.repos.extend ( new_repos )
	# --- end of load_file (...) ---

	def load ( self ):
		files = config.get_or_fail ( 'REPO.config_files' )
		for f in files:
			self.load_file ( f )
	# --- end of load (...) ---

	def sync_all ( self, package_queue=None ):
		q = None
		if package_queue is None:
			q = list()
			add = q.append
		else:
			# TODO: _nowait? raises Exception when queue is full which is
			#                good in non-threaded execution
			# -> timeout,..
			add = q.put


		# !! TODO resume here.

		for repo in self.repos:
			if repo.sync() if self.sync_enabled else repo.nosync():
				# scan repo and create package infos
				for p in repo.scan_distdir(): add ( p )
			elif self.use_broken_repos:
				# warn and scan repo
				## ..
				for p in repo.scan_distdir(): add ( p )

	# --- end of sync_all (...) ---

	def __str__ ( self ):
		return '\n'.join ( ( str ( x ) for x in self.repos ) )

