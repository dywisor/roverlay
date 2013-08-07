# R overlay -- remote, repolist
# -*- coding: utf-8 -*-
# Copyright (C) 2012 André Erdmann <dywi@mailerd.de>
# Distributed under the terms of the GNU General Public License;
# either version 2 of the License, or (at your option) any later version.

"""list-like structure for repos"""

__all__ = [ 'RepoList', ]

import re
import logging
import os.path

from roverlay import config
from roverlay.stats import collector
from roverlay.remote.repoloader import read_repofile
from roverlay.remote.basicrepo import BasicRepo

class RepoList ( object ):
   """Controls several Repo objects."""

   def __init__ ( self,
      sync_enabled=True, force_distroot=False, distroot=None
   ):
      """Initializes a RepoList.

      arguments:
      * sync_enabled  -- whether sync is enabled, defaults to True
      * force_distdir -- if set and True: put all distdirs into distroot,
                          ignoring repo-specific dirs
      * distroot      --
      """
      # if True: use all repos when looking for packages, even those that
      #           could not be synced
      self.use_broken_repos = False
      self.repos            = list()
      self.repo_stats       = collector.static.repo
      self.sync_enabled     = sync_enabled
      self.logger           = logging.getLogger ( self.__class__.__name__ )
      self.force_distroot   = force_distroot

      if distroot is None:
         self.distroot = config.get_or_fail ( "DISTFILES.root" )
      else:
         self.distroot = distroot

      # <name>_<version>.<tar suffix>
      # '^..*_[0-9.]{1,}%s$' or '^[^_]{1,}_[0-9._-]{1,}%s$'
      self.pkg_regex = re.compile (
         '^..*_..*{suffix}$'.format (
            suffix=config.get_or_fail ( 'R_PACKAGE.suffix_regex' )
         ),
         re.IGNORECASE
      )
   # --- end of __init__ (...) ---

   def _pkg_filter ( self, pkg_filename ):
      """Returns True if pkg_filename is a package, else False.

      arguments:
      * pkg_filename --
      """
      return self.pkg_regex.match ( pkg_filename ) is not None
   # --- end of _pkg_filter (...) ---

   def add_distdir ( self, distdir, src_uri=None, name=None ):
      """Adds a local package directory as BasicRepo.

      arguments:
      * distdir --
      * src_uri -- SRC_URI used in created ebuilds,
                   defaults to None which results in non-fetchable ebuilds
      * name    -- name of the repo, defaults to os.path.basename (distdir)
      """
      self.repos.append ( BasicRepo (
         name=os.path.basename ( distdir ) if name is None else name,
         directory=distdir,
         src_uri=src_uri
      ) )
   # --- end of add_distdir (...) ---

   def add_distdirs ( self, distdirs ):
      """Adds several distdirs as BasicRepos.
      All distdirs will have an invalid SRC_URI and a default name,
      use add_distdir() if you want usable ebuilds.

      arguments:
      * distdirs -- distdirs to add (must be an iterable non-str type)
      """
      def gen_repos():
         for d in distdirs:
            repo = BasicRepo (
               name=os.path.basename ( d ),
               directory=d,
               distroot=self.distroot
            )
            self.logger.debug  ( 'New entry, ' + str ( repo ) )
            yield repo
      # --- end of gen_repos() ---
      self.repos.extend ( gen_repos() )
   # --- end of add_distdirs (...) ---

   def load_file ( self, _file ):
      """Loads a repo config file and adds the repos to this RepoList.

      arguments:
      * _file --
      """
      new_repos = read_repofile ( _file,
         distroot=self.distroot,
         force_distroot=self.force_distroot
      )
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
            self.logger.warning (
               "ignoring repo {!r} (sync_status={:d}).".format (
                  repo.name, repo.sync_status
               )
            )
            return False

      for p in repo.scan_distdir ( is_package=self._pkg_filter ):
         self.logger.debug (
            "adding package {p} from repo {r}".format ( p=p, r=repo )
         )
         self.repo_stats.package_file_found ( repo )
         add_method ( p )
   # --- end of _queue_packages_from_repo (...) ---

   def add_packages ( self, add_method ):
      """Adds packages from all repos using add_method.

      arguments:
      * add_method -- method that is called for each package
      """
      addstats = self.repo_stats.queue_time
      for repo in self.repos:
         addstats.begin ( repo.name )
         self._queue_packages_from_repo ( repo, add_method )
         addstats.end ( repo.name )
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
         self.repo_stats.sync_time.begin ( repo_name )
         if repo.sync ( sync_enabled=self.sync_enabled ):
            self.repo_stats.sync_time.end ( repo.name )

            # repo successfully synced
            try_call ( when_repo_success, repo )
         else:
            self.repo_stats.sync_time.end ( repo.name )

            # else log fail <>
            try_call ( when_repo_fail, repo )

         try_call ( when_repo_done, repo )

      try_call ( when_all_done )
   # --- end of _sync_all_repos_and_run (...) ---

   def sync ( self, fail_greedy=False ):
      """Syncs all repos.

      Returns True if sync was successful for all repos, else False.

      arguments:
      * fail_greedy -- abort on first sync failure (defaults to False)
                        "screws" up time stats since sync_time should
                        include all repos
      """
      all_success = True
      self.logger.debug ( "Syncing repos ..." )
      for repo in self.repos:
         self.repo_stats.sync_time.begin ( repo.name )
         if repo.sync ( sync_enabled=self.sync_enabled ):
            self.repo_stats.sync_time.end ( repo.name )
         elif fail_greedy:
            self.repo_stats.sync_time.end ( repo.name )
            return False
         else:
            self.repo_stats.sync_time.end ( repo.name )
            all_success = False
      # -- end for
      return all_success
   # --- end of sync_all (...) ---

   def sync_and_add ( self, add_method ):
      """Syncs all repos and adds packages immediately to the package queue
      using add_method.

      arguments:
      * add_method (pkg) --
      """
      # _nowait raises Exception when queue is full which is good
      # in non-threaded execution
      qput = lambda r: self._queue_packages_from_repo ( r, add_method )

      self._sync_all_repos_and_run ( when_repo_done=qput )

   # --- end of sync_all (...) ---

   def __str__ ( self ):
      return '\n'.join ( ( str ( x ) for x in self.repos ) )
   # --- end of __str__ (...) ---
