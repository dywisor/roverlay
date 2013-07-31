# R overlay -- main()
# -*- coding: utf-8 -*-
# Copyright (C) 2012 André Erdmann <dywi@mailerd.de>
# Distributed under the terms of the GNU General Public License;
# either version 2 of the License, or (at your option) any later version.

"""main script for R overlay creation"""

__all__ = [ 'main' ]

import os
import sys
import stat

import roverlay
import roverlay.core
import roverlay.argutil
import roverlay.tools.shenv
import roverlay.stats.collector
import roverlay.util
import roverlay.config.entrymap
import roverlay.config.entryutil
import roverlay.packagerules.rules


DIE = roverlay.core.DIE
die = roverlay.core.die

def run_script_main_installed():
   return run_script_main ( True )

def run_script_main ( ROVERLAY_INSTALLED ):
   if len ( sys.argv ) < 2 or not sys.argv[0]:
      die ( "no executable specified.", DIE.USAGE )

   roverlay.core.default_helper_setup ( ROVERLAY_INSTALLED )
   roverlay.tools.shenv.run_script_exec (
      sys.argv[1], "runscript", sys.argv[1:], use_path=True
   )
# --- end of run_script_main (...) ---

def run_shell_main_installed():
   return run_shell_main ( True )

def run_shell_main ( ROVERLAY_INSTALLED ):
   config = roverlay.core.default_helper_setup ( ROVERLAY_INSTALLED )
   shell  = config.get ( 'SHELL_ENV.shell', '/bin/sh' )
   roverlay.tools.shenv.run_script_exec (
      shell, "shell", [ shell, ] + sys.argv [1:], use_path=False
   )
# --- end of run_shell_main (...) ---


def run_setupdirs ( config, target_uid, target_gid ):

   dodir            = roverlay.util.dodir
   find_config_path = roverlay.config.entryutil.find_config_path

   dirmode_private  = stat.S_IRWXU | stat.S_IRGRP | stat.S_IXGRP
   #clear_mode = ~(stat.S_IRWXU | stat.S_IRWXG | stat.S_IRWXO)
   #get_mode = lambda old, want_mode: ( old & clear_mode ) | want_mode

   WANT_USERDIR = roverlay.config.entrymap.WANT_USERDIR
   WANT_PRIVATE = roverlay.config.entrymap.WANT_PRIVATE
   WANT_FILEDIR = roverlay.config.entrymap.WANT_FILEDIR

   listlike    = lambda a: hasattr(a, '__iter__') and not isinstance(a, str)
   iter_values = lambda b: () if b is None else (b if listlike(b) else ( b, ))

   my_uid = os.getuid()
   my_gid = os.getgid()
   should_chown = my_uid != target_uid or my_gid != target_gid

   # it's not necessary to create all of the listed dirs because some of
   # them are automatically created at runtime, but doing so results in
   # a (mostly) complete filesystem layout
   #
   for config_key, entry in roverlay.config.entrymap.CONFIG_ENTRY_MAP.items():
      if isinstance ( entry, dict ) and 'want_dir_create' in entry:
         for value in iter_values (
            config.get ( find_config_path ( config_key ), None )
         ):
            dirmask = entry ['want_dir_create']
            dirpath = (
               os.path.dirname ( value.rstrip ( os.sep ) )
               if dirmask & WANT_FILEDIR else value.rstrip ( os.sep )
            )

            if dirpath:
               dodir ( dirpath )
               if dirmask & WANT_PRIVATE:
                  os.chmod ( dirpath, dirmode_private )
               if dirmask & WANT_USERDIR and should_chown:
                  os.chown ( dirpath, target_uid, target_gid )


   return os.EX_OK
# --- end of run_setupdirs (...) ---

def main_installed():
   return main ( ROVERLAY_INSTALLED=True )

def main (
   ROVERLAY_INSTALLED,
   HIDE_EXCEPTIONS=False,
   CONFIG_FILE_NAME=roverlay.core.DEFAULT_CONFIG_FILE_NAME
):
   """main() - parse args, run overlay creation, sync, ...

   arguments:
   * ROVERLAY_INSTALLED -- whether roverlay has been installed or not
   * HIDE_EXCEPTIONS    -- hide exceptions? (optional, defaults to False)
   * CONFIG_FILE_NAME   -- name of the config file (optional, defaults to
                           "R-overlay.conf")
   """
   def optionally ( call, option, *args, **kw ):
      if OPTION ( option ):
         return call ( *args, **kw )
   # --- end of optionally (...) ---

   def run_sync():
      if "sync" in actions_done: return
      try:
         # set up the repo list
         global repo_list
         repo_list = RepoList (
            sync_enabled   = not OPTION ( 'nosync' ),
            force_distroot = OPTION ( 'force_distroot' )
         )

         ## extra_opts->distdir
         if 'distdirs' in extra_opts:
            repo_list.add_distdirs ( OPTION ( 'distdirs' ) )
         else:
            # default repo list
            repo_list.load()

         ## this runs _nosync() or _sync(), depending on extra_opts->nosync
         repo_list.sync()
         set_action_done ( "sync" )

      except KeyboardInterrupt:
         die ( "Interrupted", DIE.INTERRUPT )
      except:
         if HIDE_EXCEPTIONS:
            die (
               ( "no" if OPTION ( "nosync" ) else "" ) + "sync() failed!",
               DIE.SYNC
            )
         else:
            raise
   # --- end of run_sync() ---

   def run_apply_package_rules():
      if "apply_rules" in actions_done: return

      dump_file = OPTION ( "dump_file" )
      FH        = None

      prules = PackageRules.get_configured()

      # track package rules
      prules.add_trace_actions()

      NUM_MODIFIED = 0


      BEGIN_RECEIVE_PACKAGE = ( 8 * '-' ) + " {header} " + ( 8 * '-' ) + '\n'
      #END_RECEIVE_PACKAGE   = ( 31 * '-' ) + '\n\n'

      get_header = lambda p : BEGIN_RECEIVE_PACKAGE.format (
         header = ( p ['name'] + ' ' + p ['ebuild_verstr'] )
      )
      get_footer = lambda header : ( len ( header ) - 1 ) * '-' + '\n\n'

      def tristate_counter ( f ):
         """Wrapper that returns a 2-tuple (result_list, function f').
         f' which increases result_list first, second or third
         element depending on the return value of function f (True,False,None)

         arguments:
         * f -- function to wrap
         """
         result_list = [ 0, 0, 0 ]

         def wrapped ( *args, **kwargs ):
            result = f ( *args, **kwargs )
            if result is None:
               result_list [2] += 1
            elif result:
               result_list [0] += 1
            else:
               result_list [1] += 1
            return result
         # --- end of wrapped (...) ---

         return result_list, wrapped
      # --- end of tristate_counter (...) ---

      def receive_package ( P ):
         if prules.apply_actions ( P ):
            if hasattr ( P, 'modified_by_package_rules' ):
               # ^ that check is sufficient here
               #if P.modified_by_package_rules

               receive_header = get_header ( P )

               FH.write ( receive_header )

               evars = P.get_evars()
               if evars:
                  FH.write ( "evars applied:\n" )
                  for evar in evars:
                     FH.write ( "* {}\n".format ( evar ) )

               if P.modified_by_package_rules is not True:
                  # ^ check needs to be changed when adding more trace actions
                  FH.write ( "trace marks:\n" )
                  for s in P.modified_by_package_rules:
                     if s is not True:
                        FH.write ( "* {}\n".format ( s ) )

               FH.write ( "misc data:\n" )
               for key in ( 'name', 'category', 'src_uri_dest', ):
                  FH.write (
                     "{k:<12} = {v}\n".format (
                        k=key, v=P.get ( key, "(undef)" )
                     )
                  )

               FH.write ( get_footer ( receive_header ) )

               return True
            else:
               # not modified
               return False
         else:
            receive_header = get_header ( P )
            FH.write ( receive_header )
            FH.write ( "filtered out!\n" )
            FH.write ( get_footer ( receive_header ) )
            return None

      # --- end of receive_package (...) ---

      modify_counter, receive_package_counting = (
         tristate_counter ( receive_package )
      )

      try:
         if dump_file == "-":
            FH_SHARED = True
            FH = sys.stdout
         else:
            FH_SHARED = False
            FH = open ( dump_file, 'wt' )

         repo_list.add_packages ( receive_package_counting )

         if modify_counter [0] > 0:
            FH.write ( "\n" )

         #FH.write (
         sys.stdout.write (
            'done after {t:.2f} seconds\n'
            '{p} packages processed in total, out of which\n'
            '{m} have been modified and '
            '{n} have been filtered out\n'.format (
               t = roverlay.stats.collector.static.repo.queue_time.get_total(),
               p = sum ( modify_counter ),
               m = modify_counter [0],
               n = modify_counter [2],
            )
         )

      finally:
         if 'FH' in locals() and not FH_SHARED:
            FH.close()

   # --- end of run_apply_package_rules (...) ---

   def run_overlay_create():
      if "create" in actions_done: return
      #run_sync()
      try:
         global overlay_creator
         overlay_creator = OverlayCreator (
            skip_manifest           = OPTION ( 'skip_manifest' ),
            incremental             = OPTION ( 'incremental' ),
            allow_write             = OPTION ( 'write_overlay' ),
            immediate_ebuild_writes = OPTION ( 'immediate_ebuild_writes' ),
         )

         repo_list.add_packages ( overlay_creator.add_package )
         overlay_creator.enqueue_postponed()

         overlay_creator.release_package_rules()

         if OPTION ( 'fixup_category_move' ):
            overlay_creator.remove_moved_ebuilds ( reverse=False )
         elif OPTION ( 'fixup_category_move_rev' ):
            overlay_creator.remove_moved_ebuilds ( reverse=True )

         # overlay creation should succeed after 2 runs, limit passno here
         #
         overlay_creator.run ( close_when_done=True, max_passno=2 )

         optionally ( overlay_creator.write_overlay, 'write_overlay' )
         optionally ( overlay_creator.show_overlay,  'show_overlay'  )
         if OPTION ( 'print_stats' ):
            sys.stdout.write ( '\n' )
            sys.stdout.write (
               roverlay.stats.collector.static.get_creation_str()
            )
            sys.stdout.write ( '\n\n' )
            sys.stdout.flush()


         # FIXME/TODO:
         #  this hook should be called _after_ verifying the overlay
         #  (verification is not implemented yet)
         #
         roverlay.hook.run ( 'overlay_success' )

         set_action_done ( "create" )

      except KeyboardInterrupt:
         die ( "Interrupted", DIE.INTERRUPT )
      except:
         if HIDE_EXCEPTIONS:
            die ( "Overlay creation failed.", DIE.OV_CREATE )
         else:
            raise
      finally:
         if 'overlay_creator' in locals() and not overlay_creator.closed:
            # This is important 'cause it unblocks remaining ebuild creation
            # jobs/threads, specifically waiting EbuildJobChannels in depres.
            # It also writes the deps_unresolved file
            overlay_creator.close()
   # --- end of run_overlay_create() ---

   # ********************
   #  main() starts here
   # ********************

   # get args
   try:
      # FIXME: why is the reimport of roverlay necessary?
      import roverlay
   except ImportError:
      if HIDE_EXCEPTIONS:
         die ( "Cannot import roverlay modules!", DIE.IMPORT )
      else:
         raise

   COMMAND_DESCRIPTION = {
      'sync'           : 'sync repos',
      'create'         : 'create the overlay '
                          '(implies sync, override with --nosync)',
      'depres_console' : \
         'run an interactive depres console (highly experimental)',
      'depres'         : 'this is an alias to \'depres_console\'',
      'nop'            : 'does nothing',
      'apply_rules'    : 'apply package rules verbosely and exit afterwards',
      'setupdirs'      : 'create configured directories etc.',
   }


   DEFAULT_CONFIG_FILE = roverlay.core.locate_config_file (
      ROVERLAY_INSTALLED, CONFIG_FILE_NAME
   )

   commands, config_file, additional_config, extra_opts = (
      roverlay.argutil.parse_argv (
         command_map=COMMAND_DESCRIPTION,
         default_config_file=DEFAULT_CONFIG_FILE,
      )
   )
   additional_config ['installed'] = ROVERLAY_INSTALLED

   OPTION = extra_opts.get


   # -- determine commands to run
   # (TODO) could replace this section when adding more actions
   # imports roverlay.remote, roverlay.overlay.creator

   actions = set ( filter ( lambda x : x != 'nop', commands ) )
   actions_done = set()
   set_action_done = actions_done.add

   want_logging = True
   do_setupdirs = False

   if 'sync' in actions and OPTION ( 'nosync' ):
      die ( "sync command blocked by --nosync opt.", DIE.ARG )

   elif 'setupdirs' in actions:
      do_setupdirs = True
      want_logging = False
      if len ( actions ) > 1:
         die ( "setupdirs cannot be run with other commands!", DIE.USAGE )

   del commands


   if not actions:
      # this happens if a command is nop
      die ( "Nothing to do!", DIE.NOP )

   # -- load config

   # imports: roverlay, roverlay.config.entryutil (if --help-config)

   try:
      roverlay.stats.collector.static.time.begin ( "setup" )
      roverlay.core.setup_initial_logger()

      conf = roverlay.core.load_config_file (
         config_file,
         extraconf      = additional_config,
         setup_logger   = want_logging,
         load_main_only = do_setupdirs,
      )
      del config_file, additional_config
   except:
      if not config_file:
         sys.stderr.write ( '!!! No config file found.\n' )

      if HIDE_EXCEPTIONS:
         die (
            "Cannot load config file {!r}.".format ( config_file ), DIE.CONFIG
         )
      else:
         raise
   else:
      roverlay.stats.collector.static.time.end ( "setup" )

   if do_setupdirs:
      sys.exit ( run_setupdirs (
         conf, extra_opts['target_uid'], extra_opts['target_gid']
      ) )
   # -- end commands with partial config / without logging

   if OPTION ( 'list_config' ):
      try:
         from roverlay.config.entryutil import list_entries
         print ( "== main config file ==\n" )
         print ( list_entries() )
      except:
         raise
         die ( "Cannot list config entries!" )

      EXIT_AFTER_CONFIG = True

   if OPTION ( 'print_config' ):
      try:
         conf.visualize ( into=sys.stdout )
      except:
         die ( "Cannot print config!" )
      EXIT_AFTER_CONFIG = True

   if OPTION ( 'print_package_rules' ):
      # no try-/catch block here

      package_rules = (
         roverlay.packagerules.rules.PackageRules.get_configured()
      )

      HLINE = "".rjust ( 79, '-' )
      print ( HLINE )
      print ( str ( package_rules ) )
      print ( HLINE )

      EXIT_AFTER_CONFIG = True

   # -- end of EXIT_AFTER_CONFIG entries

   if 'EXIT_AFTER_CONFIG' in locals() and EXIT_AFTER_CONFIG:
      sys.exit ( os.EX_OK )

   # switch to depres console
   elif 'depres_console' in actions or 'depres' in actions:
      if len ( actions ) != 1:
         die ( "depres_console cannot be run with other commands!", DIE.USAGE )

      try:
         from roverlay.console.depres import DepresConsole
         con = DepresConsole()
         con.setup ( config=conf )
         try:
            con.run_forever()
            set_action_done ( "depres_console" )
         finally:
            con.close()

      except ImportError:
         if HIDE_EXCEPTIONS:
            die ( "Cannot import depres console!", DIE.IMPORT )
         else:
            raise
      except:
         if HIDE_EXCEPTIONS:
            die ( "Exiting on console error!", DIE.ERR )
         else:
            raise

   else:
      # sync/create
      # -- import roverlay modules

      try:
         from roverlay.remote          import RepoList
         from roverlay.overlay.creator import OverlayCreator

         import roverlay.config
         import roverlay.hook
      except ImportError:
         if HIDE_EXCEPTIONS:
            die ( "Cannot import roverlay modules!", DIE.IMPORT )
         else:
            raise

      # -- run methods (and some vars)
      # imports: package rules

      #repo_list       = None
      #overlay_creator = None

      # -- run

      # initialize roverlay.hook
      roverlay.hook.setup()

      # initialize database
      STATS_DB_FILE = conf.get ( 'RRD_DB.file', None )
      if STATS_DB_FILE:
         roverlay.stats.collector.static.setup_database ( conf )
         want_db_commit = False

      # always run sync 'cause commands = {create,sync,apply_rules}
      # and create,apply_rules implies (no)sync
      run_sync()

      if "apply_rules" in actions:
         from roverlay.packagerules.rules import PackageRules
         run_apply_package_rules()
      elif 'create' in actions:
         run_overlay_create()
         want_db_commit = True


      if STATS_DB_FILE and want_db_commit:
         roverlay.stats.collector.static.write_database()
         roverlay.hook.run ( 'db_written' )


      # *** TEMPORARY ***
      if OPTION ( 'dump_stats' ):
         print ( "\n{:-^60}".format ( " stats dump " ) )
         print ( roverlay.stats.collector.static )
         print ( "{:-^60}".format ( " end stats dump " ) )
      # *** END TEMPORARY ***


   if len ( actions ) > len ( actions_done ):
      die (
         "Some actions (out of {!r}) could not be performed!".format (
            actions ), DIE.CMD_LEFTOVER
      )
# --- end of main (...) ---
