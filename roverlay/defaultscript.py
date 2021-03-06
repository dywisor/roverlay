# R overlay -- main()
# -*- coding: utf-8 -*-
# Copyright (C) 2013 André Erdmann <dywi@mailerd.de>
# Distributed under the terms of the GNU General Public License;
# either version 2 of the License, or (at your option) any later version.

from __future__ import print_function

import os
import sys
import logging

import roverlay.config.entrymap
import roverlay.config.entryutil
import roverlay.core
import roverlay.console.depres
import roverlay.hook
import roverlay.overlay.creator
import roverlay.overlay.pkgdir.distroot.static
import roverlay.packagerules.rules
import roverlay.recipe.distmap
import roverlay.remote.repolist
import roverlay.runtime
import roverlay.tools.shenv
import roverlay.util

from roverlay.core import DIE, die


# ===============
#  main routines
# ===============

def main_installed ( *args, **kw ):
   return main ( True, *args, **kw )
# --- end of main_installed (...) ---

def main ( installed, *args, **kw ):
   main_env = roverlay.runtime.RuntimeEnvironment ( installed, *args, **kw )
   main_env.setup()

   if run_early_commands ( main_env ):
      sys.exit ( os.EX_OK )

   elif (
      main_env.want_command ( 'depres_console' ) or
      main_env.want_command ( 'depres' )
   ):
      con = roverlay.console.depres.DepresConsole()
      con.setup ( config=main_env.config )
      try:
         con.run_forever()
      finally:
         con.close()

      sys.exit ( os.EX_OK )

   elif main_env.want_command ( 'distmap_rebuild' ):
      sys.exit ( run_distmap_rebuild ( main_env ) )

   elif main_env.want_command ( 'apply_rules' ):
      sys.exit ( run_apply_package_rules ( main_env ) )

   else:
      roverlay.hook.setup()
      main_env.setup_database()

      retcode = os.EX_OK

      if main_env.want_command ( 'sync' ):
         retcode = run_sync ( main_env )
      elif main_env.want_command ( 'create' ):
         retcode = run_overlay_create ( main_env )
      else:
         die ( "unknown command: {!r}".format ( main_env.command ) )

      main_env.write_database()
      main_env.dump_stats()
      sys.exit ( retcode )
# --- end of main (...) ---

def run_script_main_installed ( *args, **kw ):
   return run_script_main ( True, *args, **kw )
# --- end of run_script_main_installed (...) ---

def run_script_main ( installed ):
   if len ( sys.argv ) < 2 or not sys.argv[0]:
      die ( "no executable specified.", DIE.USAGE )

   exe = sys.argv[1]
   script_file = os.path.abspath ( exe )
   if os.path.isfile ( script_file ) or os.sep in exe:
      exe = script_file

   roverlay.core.default_helper_setup ( installed )
   roverlay.tools.shenv.run_script_exec (
      exe, "runscript", sys.argv[1:], use_path=True
   )
# --- end of run_script_main (...) ---

def run_shell_main_installed ( *args, **kw ):
   return run_shell_main ( True, *args, **kw )

def run_shell_main ( installed ):
   config = roverlay.core.default_helper_setup ( installed )
   shell  = config.get ( 'SHELL_ENV.shell', '/bin/sh' )
   roverlay.tools.shenv.run_script_exec (
      shell, "shell", [ shell, ] + sys.argv [1:], use_path=False
   )
# --- end of run_shell_main (...) ---


# ==============
#  sub routines
# ==============

def run_early_commands ( env ):
   want_exit = False

   if env.options ['list_config_entries']:
      want_exit = True
      print ( "== main config file ==\n" )
      print ( roverlay.config.entryutil.list_entries() )

   if env.options ['print_config']:
      want_exit = True
      env.config.visualize ( into=sys.stdout )

   if env.options ['print_package_rules']:
      want_exit = True
      package_rules = (
         roverlay.packagerules.rules.PackageRules.get_configured()
      )
      env.add_addition_control_rules ( package_rules )

      print ( env.HLINE )
      print ( str ( package_rules ) )
      print ( env.HLINE )

   return want_exit
# --- end of run_early_commands (...) ---


def run_distmap_rebuild ( env ):
   if env.action_done ( 'distmap_rebuild' ):
      return os.EX_OK

   roverlay.core.force_console_logging ( logging.INFO )

   roverlay.recipe.distmap.setup()
   distroot = None
   try:
      distroot = roverlay.overlay.pkgdir.distroot.static.get_configured()
      distroot.check_integrity()
   finally:
      if distroot is not None:
         distroot.finalize()

   return os.EX_OK
# --- end of run_distmap_rebuild (...) ---

def run_sync ( env ):
   if env.action_done ( 'sync' ):
      return

   STRICT_SYNC = env.option ( 'strict' ) or env.option ( 'strict_sync' )

   try:
      # set up the repo list
      repo_list = env.get_repo_list()

      ## extra_opts->distdir
      if 'distdirs' in env.options:
         repo_list.add_distdirs ( env.option ( 'distdirs' ) )
      else:
         # default repo list
         repo_list.load()

      ## this runs _nosync() or _sync(), depending on extra_opts->nosync
      sync_success = repo_list.sync ( fail_greedy=STRICT_SYNC )
      env.set_action_done ( "sync" )

   except KeyboardInterrupt:
      die ( "Interrupted", DIE.INTERRUPT )
   except:
      if env.hide_exceptions:
         die (
            ( "no" if env.option ( "nosync" ) else "" ) + "sync() failed!",
            DIE.SYNC
         )
      else:
         raise
   else:
      if not sync_success and STRICT_SYNC:
         die ( "errors occured while syncing.", DIE.SYNC )
# --- end of run_sync() ---

def run_overlay_create ( env ):
   if env.action_done ( "create" ):
      return
   run_sync ( env )

   repo_list       = None
   overlay_creator = None

   try:
      repo_list       = env.get_repo_list()
      overlay_creator = env.get_overlay_creator()
      env.add_addition_control_to_overlay_creator()

      ebuild_import_nosync = env.option ( 'sync_imported' )
      if ebuild_import_nosync is None:
         ebuild_import_nosync = env.config.get_or_fail ( 'nosync' )
      else:
         ebuild_import_nosync = not ebuild_import_nosync


      overlay_creator.overlay.import_ebuilds (
         overwrite = not env.option ( 'incremental' ),
         nosync    = ebuild_import_nosync,
      )

      repo_list.add_packages ( overlay_creator.add_package )
      if env.options ['revbump']:
         overlay_creator.enqueue_postponed()
      else:
         overlay_creator.discard_postponed()

      overlay_creator.release_package_rules()

      if env.options ['fixup_category_move']:
         overlay_creator.remove_moved_ebuilds ( reverse=False )
      elif env.options ['fixup_category_move_reverse']:
         overlay_creator.remove_moved_ebuilds ( reverse=True )

      # overlay creation should succeed after 2 runs, limit passno here
      #
      overlay_creator.run ( close_when_done=True, max_passno=2 )

      if env.options ['write_overlay']:
         overlay_creator.write_overlay()

      if env.options ['show_overlay']:
         overlay_creator.show_overlay()

      if env.options ['print_stats']:
         sys.stdout.write ( '\n' )
         sys.stdout.write ( env.stats.get_creation_str() )
         sys.stdout.write ( '\n\n' )
         sys.stdout.flush()


      # FIXME/TODO:
      #  this hook should be called _after_ verifying the overlay
      #  (verification is not implemented yet)
      #
      roverlay.hook.run ( 'overlay_success' )

      env.want_db_commit = True
      env.set_action_done ( "create" )

   except KeyboardInterrupt:
      die ( "Interrupted", DIE.INTERRUPT )
   except:
      if env.hide_exceptions:
         die ( "Overlay creation failed.", DIE.OV_CREATE )
      else:
         raise
   finally:
      if overlay_creator is not None and not overlay_creator.closed:
         # This is important 'cause it unblocks remaining ebuild creation
         # jobs/threads, specifically waiting EbuildJobChannels in depres.
         # It also writes the deps_unresolved file
         overlay_creator.close()
# --- end of run_overlay_create() ---

def run_apply_package_rules ( env ):
   if env.action_done ( 'apply_rules' ):
      return
   run_sync ( env )

   dump_file = env.option ( "dump_file" )
   FH        = None

   prules = roverlay.packagerules.rules.PackageRules.get_configured()
   env.add_addition_control_rules ( prules )

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

            if P.depconf:
               FH.write ( "dependencies manipulated:\n" )
               for root_key, subdict in P.depconf.items():
                  if subdict:
                     klen = max ( len(s) for s in subdict.keys() )

                     FH.write ( "* {k}\n".format ( k=root_key ) )
                     for key, deplist in sorted (
                        subdict.items(), key=( lambda kv: kv[0] ),
                     ):
                        for dep in deplist:
                           FH.write (
                              "  {key:<{l}} += \"{dep}\"\n".format (
                                 key=key, dep=dep, l=klen
                              )
                           )


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

            FH.write (
               "{k:<12} = {v}\n".format (
                  k = "add-policy",
                  v = (
                     getattr ( P, 'overlay_addition_override', None )
                        or "(undef)"
                  ),
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

   FH_SHARED = True
   try:
      if dump_file == "-":
         FH = sys.stdout
      else:
         FH_SHARED = False
         FH = open ( dump_file, 'wt' )

      env.get_repo_list().add_packages ( receive_package_counting )

      if modify_counter [0] > 0:
         FH.write ( "\n" )

      #FH.write (
      sys.stdout.write (
         'done after {t:.2f} seconds\n'
         '{p} packages processed in total, out of which\n'
         '{m} have been modified and '
         '{n} have been filtered out\n'.format (
            t = env.stats.repo.queue_time.get_total(),
            p = sum ( modify_counter ),
            m = modify_counter [0],
            n = modify_counter [2],
         )
      )

   finally:
      if FH and not FH_SHARED:
         FH.close()

# --- end of run_apply_package_rules (...) ---
