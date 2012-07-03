import re
import logging

from roverlay import config
from roverlay.remote.repoloader import read_repofile

class RepoList ( object ):
	"""Controls several Repo objects."""

	def __init__ ( self, sync_enabled=True ):
		self.repos = list()

		self.sync_enabled = sync_enabled

		self.logger = logging.getLogger ( self.__class__.__name__ )

		# if True: use all repos when looking for packages, even those that
		#           could not be synced
		self.use_broken_repos = False


		# <name>_<version>.<tar suffix>
		# '^..*_[0-9.]{1,}%s$' or '^[^_]{1,}_[0-9._-]{1,}%s$'
		self.pkg_regex = re.compile (
			'^..*_..*%s$' % config.get_or_fail ( 'R_PACKAGE.suffix_regex' ),
		)
	# --- end of __init__ (...) ---

	def _pkg_filter ( self, pkg_filename ):
		"""Returns True if pkg_filename is a package, else False.

		arguments:
		* pkg_filename --
		"""
		return self.pkg_regex.match ( pkg_filename ) is not None
	# --- end of _pkg_filter (...) ---

	def load_file ( self, _file ):
		"""Loads a repo config file and adds the repos to this RepoList.

		arguments:
		* _file --
		"""
		new_repos = read_repofile ( _file )
		if new_repos:
			self.repos.extend ( new_repos )
	# --- end of load_file (...) ---

	def load ( self ):
		"""Loads the default repo config files
		(as listed in the main configuration file).
		"""
		files = config.get_or_fail ( 'REPO.config_files' )
		for f in files:
			self.load_file ( f )
	# --- end of load (...) ---

	def _queue_packages_from_repo ( self, repo, add_method ):
		"""Adds all packages from a repo using add_method.

		arguments:
		* repo       --
		* add_method -- method that is called for each package,
		                has to accept exactly one arg, the package
		"""
		if not repo.ready():
			if self.use_broken_repos:
				# warn and continue
				pass
			else:
				# repo cannot be used
				self.logger.warning ( "ignoring repo %s." % repo.name )
				return False

		for p in repo.scan_distdir ( is_package=self._pkg_filter ):
			self.logger.debug ( "adding package %s from repo %s" % ( p, repo ) )
			add_method ( p )
	# --- end of _queue_packages_from_repo (...) ---

	def add_packages ( self, add_method ):
		"""Adds packages from all repos using add_method.

		arguments:
		* add_method -- method that is called for each package
		"""

		for repo in self.repos:
			self._queue_packages_from_repo ( repo, add_method )
	# --- end of add_packages (...) ---

	def _sync_all_repos_and_run (
		self,
		when_repo_success=None, when_repo_fail=None, when_repo_done=None,
		when_all_done=None
	):
		"""A method that syncs all repos and is able to call other methods
		on certain events (repo done/success/fail, all done).

		arguments:
		* when_repo_success (pkg) -- called after a successful repo sync
		* when_repo_fail    (pkg) -- called after an unsuccessful repo sync
		* when_repo_done    (pkg) -- called when a repo sync has finished
		* when_all_done     (pkg) -- called when all repo sync have finished
		"""

		# try_call (f,*args,**kw) calls f (*args,**kw) unless f is None
		try_call = lambda f, *x, **z : None if f is None else f ( *x, **z )

		self.logger.debug ( "Syncing repos ..." )
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
		"""Syncs all repos."""
		self.logger.debug ( "Syncing repos ..." )
		for repo in self.repos:
			repo.sync ( sync_enabled=self.sync_enabled )
	# --- end of sync_all (...) ---

	def sync_and_add ( self, add_method ):
		"""Syncs all repos and adds packages immediately to the package queue
		using add_method.

		arguments:
		* add_method (pkg) --
		"""
		# TODO: _nowait? raises Exception when queue is full which is
		#                good in non-threaded execution
		# -> timeout,..

		qput = lambda r: self._queue_packages_from_repo ( r, add_method )

		self._sync_all_repos_and_run ( when_repo_done=qput )

	# --- end of sync_all (...) ---

	def __str__ ( self ):
		return '\n'.join ( ( str ( x ) for x in self.repos ) )
	# --- end of __str__ (...) ---
