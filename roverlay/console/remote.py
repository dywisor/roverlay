# R overlay --
# -*- coding: utf-8 -*-
# Copyright (C) 2013 André Erdmann <dywi@mailerd.de>
# Distributed under the terms of the GNU General Public License;
# either version 2 of the License, or (at your option) any later version.

import os
import sys

import roverlay.console.base
import roverlay.console.interpreter
from roverlay.console.interpreter import ConsoleInterpreter

import roverlay.strutil
from roverlay.strutil import unquote, unquote_all


class RemoteConsoleInterpreter ( ConsoleInterpreter ):

   CHROOT_ALLOWED = tuple()

   def __init__ ( self, *args, **kwargs ):
      ConsoleInterpreter.__init__ ( self, *args, **kwargs )
      self.intro = "remote console (INCOMPLETE)"
   # --- end of __init__ (...) ---

   def setup_aliases ( self ):
      ConsoleInterpreter.setup_aliases ( self )
      self.add_alias ( "sync", "s" )
      self.add_alias ( "load_conf", "lc" )
   # --- end of setup_aliases (...) ---

   def setup_argparser ( self ):
      ConsoleInterpreter.setup_argparser ( self )

      # sync
      parser = self.get_argparser ( "sync", create=True )
      parser.add_argument ( "repos", nargs="*", metavar="<name>",
         help="specify repos to sync"
      )

      # query
      parser = self.get_argparser ( "query", create=True )
      parser.add_argument ( "repos", nargs="*", metavar="<name>",
         help="specify repos to query"
      )
   # --- end of setup_argparser (...) ---

   def do_load_conf ( self, line ):
      """Load configured repo files."""
      if not self.interface.load_configured ( ignore_missing=True ):
         sys.stderr.write ( "failed to load repo config!\n" )
   # --- end of do_load_conf (...) ---

   def do_sync ( self, line ):
      """Syncs repos. See --help for usage."""
      args = self.parse_cmdline ( "sync", line )
      if args is not None:
         if args.repos:
            rlist = list ( filter ( None, args.repos ) )
            if rlist:
               sys.stdout.write (
                  "Syncing repos: {} ... \n".format ( ', '.join ( rlist ) )
               )
               self.interface.sync ( repo_filter=lambda r: r.name in rlist )
         else:
            sys.stdout.write ( "Syncing all repos ... \n" )
            self.interface.sync()
   # --- end of do_sync (...) ---

   def do_online ( self, line ):
      """Enables syncing with remotes."""
      self.interface.enable_sync()
   # --- end of do_online (...) ---

   def do_offline ( self, line ):
      """Disables syncing with remotes."""
      self.interface.disable_sync()
   # --- end of do_offline (...) ---

   def do_query ( self, line ):
      """Query repo status. See --help for detailed usage."""
      def report_repo ( repo ):
         ready  = repo.ready()
         status = repo.sync_status

         sys.stdout.write ( ( 60 * '-' ) + '\n' )
         sys.stdout.write ( "repo: {!s}\n".format ( ( repo ) ) )
         if not ready:
            sys.stdout.write (
               "{n} would be ignored!\n".format ( n=repo.name )
            )

         sys.stdout.write (
            "{n}.ready() = {r} (sync_status={s:d})\n\n".format (
               n=repo.name, r=ready, s=status,
            )
         )

      args = self.parse_cmdline ( "query", line )
      if args is None:
         pass
      elif args.repos:
         for repo_name in args.repos:
            lrepo = self.interface.get_repos_by_name ( repo_name )
            if len ( lrepo ) > 1:
               sys.stderr.write (
                  "found multiple repos for {!r}!\n".format ( repo_name )
               )
            elif lrepo:
               report_repo ( lrepo[0] )
            else:
               sys.stderr.write (
                  "*** no such repo: {!r} ***\n".format ( repo_name )
               )
      else:
         for repo in self.interface.repos:
            report_repo ( repo )
   # --- end of do_query (...) ---

   def do_query_packages ( self, line ):
      """Count packages and print the result."""
      self.interface.STATS.repo.reset()
      self.interface.repolist.add_packages ( lambda *a, **b: None )
      sys.stdout.write ( str ( self.interface.STATS.repo ) )
      sys.stdout.write ( "\n" )
   # --- end of do_query_packages (...) ---

# --- end of RemoteConsoleInterpreter ---

class RemoteConsole ( roverlay.console.base.MainConsole ):
   INTERPRETER_CLS = RemoteConsoleInterpreter

   def get_interface ( self ):
      return self.root_interface.spawn_interface ( "remote" )
   # --- end of get_interface (...) ---

# --- end of DepresConsole ---
