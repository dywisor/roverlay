# R overlay -- remote interface
# -*- coding: utf-8 -*-
# Copyright (C) 2013 André Erdmann <dywi@mailerd.de>
# Distributed under the terms of the GNU General Public License;
# either version 2 of the License, or (at your option) any later version

import errno

import roverlay.interface.generic

import roverlay.remote.repolist
import roverlay.remote.status


class RemoteInterface ( roverlay.interface.generic.RoverlaySubInterface ):
   #
   # Note: this interface is a stub, it supports syncing only!
   #

   CONFIG_KEY_REPOS = 'REPO.config_files'

   SYNC_SUCCESS = roverlay.remote.status.SYNC_SUCCESS
   SYNC_FAIL    = roverlay.remote.status.SYNC_FAIL
   SYNC_DONE    = roverlay.remote.status.SYNC_DONE
   REPO_READY   = roverlay.remote.status.REPO_READY

   def __init__ ( self, parent_interface ):
      super ( RemoteInterface, self ).__init__ ( parent_interface )
      self._repolist = roverlay.remote.repolist.RepoList (
         sync_enabled=self.config.get_or_fail ( "nosync" )
      )
   # --- end of __init__ (...) ---

   @property
   def repolist ( self ):
      """direct access to the RepoList"""
      return self._repolist

   @property
   def repos ( self ):
      """direct access to the repos"""
      return self._repolist.repos

   @property
   def sync_enabled ( self ):
      return self._repolist.sync_enabled

   def _set_sync ( self, status ):
      """Enables/Disables syncing.

      Returns: old sync enable status

      arguments:
      * status -- new sync enable status
      """
      old_sync_enable = self._repolist.sync_enabled
      self._repolist.sync_enabled = bool ( status )
      return old_sync_enable
   # --- end of _set_sync (...) ---

   def enable_sync ( self ):
      """Enables syncing.

      Returns: old sync enable status
      """
      return self._set_sync ( True )
   # --- end of enable_sync (...) ---

   def disable_sync ( self ):
      """Disables syncing.

      Returns: old sync enable status
      """
      return self._set_sync ( False )
   # --- end of disable_sync (...) ---

   def load_repo_file ( self, filepath, ignore_missing=False ):
      """Loads a repo file.

      Returns True on success, else False.

      arguments:
      * filepath       -- path to the repo config file
      * ignore_missing -- suppress exceptions caused by missing files
      """
      if ignore_missing:
         try:
            self._repolist.load_file ( filepath )
         except OSError as oserr:
            if oserr.errno == errno.ENOENT:
               return False
            else:
               raise
         else:
            return True
      else:
         self._repolist.load_file ( filepath )
         return True
   # --- end of load_repo_file (...) ---

   def load_repo_files ( self, files, ignore_missing=False ):
      """Loads zero or more repo files.

      Returns: True if loading of all files succeeded, else False.

      arguments:
      * files          -- files to load
      * ignore_missing -- suppress exceptions caused by missing files
      """
      ret = True
      for filepath in files:
         if not self.load_repo_file ( filepath ):
            ret = False
      return ret
   # --- end of load_repo_files (...) ---

   def load_configured ( self, ignore_missing=False ):
      """Loads the configured repo files.

      Returns: success (True/False)

      arguments:
      * ignore_missing -- suppress exceptions caused by missing files
                          Additionally, do not fail if no repo files
                          configured.
      """
      if ignore_missing:
         files = self.config.get ( self.CONFIG_KEY_REPOS, None )
         if files is not None:
            return self.load_repo_files ( files, ignore_missing=True )
         else:
            return True
      else:
         return self.load_repo_files (
            self.config.get_or_fail ( self.CONFIG_KEY_REPOS ),
            ignore_missing=False
         )
   # --- end of load_configured (...) ---

   def sync ( self, enable_sync=None, repo_filter=None ):
      """Syncs all repos (or a subset of them).

      Returns: success (True/False)

      arguments:
      * enable_sync -- enable/disable syncing
                        Defaults to None (-> use RepoList default)
      * repo_filter -- filter for choosing which repos to sync
                        Defaults to None (-> do not filter)
      """
      sync_enabled = bool (
         self._repolist.sync_enabled if enable_sync is None else enable_sync
      )

      success = True
      for repo in (
         self._repolist.repos if repo_filter is None
         else filter ( repo_filter, self._repolist.repos )
      ):
         repo.reset()
         if not repo.sync ( sync_enabled ):
            success = False

      return success
   # --- end of sync (...) ---

   def sync_named_repo ( self, repo_name, enable_sync=None ):
      """Syncs all repos with the given name.

      Returns: success (True/False)

      arguments:
      * repo_name   -- name of the repo
      * enable_sync -- enable/disable syncing
      """
      return self.sync (
         enable_sync=enable_sync,
         repo_filter=lambda r: r.name == repo_name
      )
   # --- end of sync_named_repo (...) ---

   def sync_online ( self, repo_filter=None ):
      """Calls sync with enable_sync=True."""
      return self.sync ( enable_sync=True, repo_filter=repo_filter )
   # --- end of sync_online (...) ---

   def sync_offline ( self, repo_filter=None ):
      """Calls sync with enable_sync=False."""
      return self.sync ( enable_sync=False, repo_filter=repo_filter )
   # --- end of sync_offline (...) ---

   def get_repos_by_name ( self, repo_name ):
      """Returns a list containing all repos with the given name.

      arguments:
      * repo_name --
      """
      return [ r for r in self._repolist.repos if r.name == repo_name ]
   # --- end of get_repos_by_name (...) ---

   def get_repo_by_name ( self, repo_name ):
      """Returns the repo with the given name. Returns None if no such repo
      exists.

      arguments:
      * repo_name --
      """
      rlist = self.get_repos_by_name ( repo_name )
      return rlist[0] if rlist else None
   # --- end of get_repo_by_name (...) ---

# --- end of RemoteInterface ---
