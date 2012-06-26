import logging

from roverlay import config
from roverlay.remote.repoloader import read_repofile

LOGGER = logging.getLogger ( 'RepoList' )

class RepoList ( object ):

	def __init__ ( self ):
		self.repos = list()

		self.sync_enabled = True

		# if True: use all repos when looking for packages, even those that
		#           could not be synced
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

	def _queue_packages_from_repo ( self, repo, add_method ):
		if not repo.ready():
			if self.use_broken_repos:
				# warn and continue
				pass
			else:
				# repo cannot be used
				LOGGER.warning ( "!!" )
				return False

		for p in repo.scan_distdir():
			LOGGER.debug ( "adding package %s from repo %s" % ( p, repo ) )
			add_method ( p )
	# --- end of _queue_packages_from_repo (...) ---

	def add_packages ( self, add_method ):
		for repo in self.repos:
			self._queue_packages_from_repo ( repo, add_method )
	# --- end of add_packages (...) ---

	def _sync_all_repos_and_run (
		self,
		when_repo_success=None, when_repo_fail=None, when_repo_done=None,
		when_all_done=None
	):
		try_call = lambda f, *x, **z : None if f is None else f ( *x, **z )

		LOGGER.debug ( "Syncing repos ..." )
		for repo in self.repos:
			if repo.sync ( sync_enabled=self.sync_enabled ):
				# repo successfully synced
				try_call ( when_repo_success, repo )
			else:
				# else log fail <>
				try_call ( when_repo_fail, repo )

			try_call ( when_repo_done, repo )

		try_call ( when_all_done )
	# --- end of _sync_all_repos_and_run (...) ---

	def sync ( self ):
		LOGGER.debug ( "Syncing repos ..." )
		for repo in self.repos:
			repo.sync ( sync_enabled=self.sync_enabled )
	# --- end of sync_all (...) ---

	def sync_and_add ( self, add_method ):
		"""Syncs all repos and adds packages immediately to the package queue."""
		# TODO: _nowait? raises Exception when queue is full which is
		#                good in non-threaded execution
		# -> timeout,..

		qput = lambda r: self._queue_packages_from_repo ( r, add_method )

		self._sync_all_repos_and_run ( when_repo_done=qput )

	# --- end of sync_all (...) ---

	def __str__ ( self ):
		return '\n'.join ( ( str ( x ) for x in self.repos ) )

