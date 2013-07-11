# R overlay -- tools, shell script environment
# -*- coding: utf-8 -*-
# Copyright (C) 2013 André Erdmann <dywi@mailerd.de>
# Distributed under the terms of the GNU General Public License;
# either version 2 of the License, or (at your option) any later version.

import logging
import os
import subprocess
import tempfile
import time


import roverlay.config
import roverlay.strutil
import roverlay.util


# _SHELL_ENV, _SHELL_INTPR are created when calling run_script()
#
_SHELL_ENV   = None
#_SHELL_INTPR = None
LOGGER       = logging.getLogger ( 'shenv' )

NULL_PHASE = 'null'


# shell env dict quickref
#  TODO: move this to doc/
#
# $PATH, $LOGNAME, $SHLVL, $TERM, [$PWD], $HOME
#
#  taken from os.environ
#
# $ROVERLAY_PHASE
#
#  hook phase (set in run_script())
#
# $OVERLAY == $S
#
#  overlay directory (depends on config value), initial directory for scripts
#
# $OVERLAY_NAME
#
#  name of the overlay
#
# $DISTROOT
#
#  mirror directory (depends on config value)
#
# $TMPDIR == $T
#
#  depends on config value (+fallback)
#
# $ADDITIONS_DIR == $FILESDIR (optional)
#
#  depends on config value
#
# $SHLIB (optional)
#
#  shell functions dir (if found, ${ADDITIONS_DIR}/shlib)
#
# $FUNCTIONS (optional)
#
#  core functions file (if found, ${ADDITIONS_DIR}/{shlib,}/functions.sh)
#
# $EBUILD
#
#  ebuild executable, depends on config value
#
# $GIT_EDITOR
# $GIT_ASKPASS
#
#  set to /bin/false
#
# $NOSYNC
#
#  depends on config value
#
# $NO_COLOR
#
#  alway false ('n')
#
# $DEBUG
# $VERBOSE
# $QUIET
#
#  shbools that indicate whether debug/verbose/quiet ouput is desired,
#  depends on log level
#


def setup_env():
   """Returns a 'well-defined' env dict for running scripts."""

   ROVERLAY_INSTALLED = roverlay.config.get_or_fail ( 'installed' )
   SHLIB_DIRNAME      = 'shlib'
   SHFUNC_FILENAME    = 'functions.sh'

   # @typedef shbool is SH_TRUE|SH_FALSE, where:
   SH_TRUE  = 'y'
   SH_FALSE = 'n'

   def shbool ( value ):
      """Converts value into a shbool."""
      return SH_TRUE if value else SH_FALSE
   # --- end of shbool (...) ---

   # import os.environ
   if roverlay.config.get ( "SHELL_ENV.filter_env", True ):
      # (keepenv does not support wildcars)
      env = roverlay.util.keepenv (
         ( 'PATH', '/usr/local/bin:/usr/bin:/bin' ),
         'PWD',
         'LOGNAME',
         'SHLVL',
         'TERM',
         'HOME',
         # what else?
      )
      #
      # LANG, LC_ALL, LC_COLLATE, ...
      #
      # GIT_AUTHOR_NAME, GIT_AUTHOR_EMAIL,
      # GIT_COMMITTER_NAME, GIT_COMMITTER_EMAIL, ...
      #
      # GIT_EDITOR and GIT_ASKPASS are set to /bin/false here
      #

   else:
      env = dict ( os.environ )

   # setup* functions
   def setup ( k, v ):
      env [k] = v

   def setup_conf ( k, c ):
      env [k] = roverlay.config.get_or_fail ( c )

   def setup_self ( k, c ):
      env[k] = env[c]

   ## create shell vars

   # str $ROVERLAY_PHASE
   #  properly defined in shenv_run()
   #
   setup ( 'ROVERLAY_PHASE', NULL_PHASE )

   # str::dirpath $OVERLAY
   setup_conf ( 'OVERLAY', 'OVERLAY.dir' )

   # str::dirpath $S renames $OVERLAY
   setup_self ( 'S', 'OVERLAY' )

   # str $OVERLAY_NAME
   setup_conf ( 'OVERLAY_NAME', 'OVERLAY.name' )

   # str::dirpath $HOME renames $OVERLAY
   #
   #  FIXME: this should/could be the parent dir of $OVERLAY
   #  FIXME: git wants to read $HOME/.gitconfig
   #
   ##setup_self ( 'HOME', 'OVERLAY' )

   # str::dirpath $DISTROOT
   setup_conf ( 'DISTROOT', 'OVERLAY.DISTDIR.root' )

   # str::dirpath $TMPDIR := <default>
   setup (
      'TMPDIR',
      roverlay.config.get ( 'OVERLAY.TMPDIR.root' ) or tempfile.gettempdir()
   )

   # str::dirpath $T renames $TMPDIR
   setup_self ( 'T', 'TMPDIR' )

   # @optional str::dirpath $ADDITIONS_DIR
   # @optional str::dirpath $FILESDIR renames $ADDITIONS_DIR
   #
   # @optional str::dirpath $SHLIB is ${ADDITIONS_DIR}/shlib
   #  directory with shell function files
   #
   # @optional str::filepath $FUNCTIONS is <see below>
   #  shell file with "core" functions
   #
   additions_dir = roverlay.config.get ( 'OVERLAY.additions_dir', None )
   shlib_path    = []

   if ROVERLAY_INSTALLED:
      installed_shlib = (
         roverlay.config.get_or_fail ( 'INSTALLINFO.libexec' )
         + os.sep + SHLIB_DIRNAME
      )
      if os.path.isdir ( installed_shlib ):
         shlib_path.append ( installed_shlib )
         shlib_file = installed_shlib + os.sep + SHFUNC_FILENAME
         if os.path.isfile ( shlib_file ):
            setup ( 'FUNCTIONS', shlib_file )
         else:
            LOGGER.error (
               "roverlay is installed, but $FUNCTIONS file is missing."
            )
      else:
         LOGGER.error ( "roverlay is installed, but shlib dir is missing." )
   # -- end if installed~shlib

   if additions_dir:
      setup ( 'ADDITIONS_DIR', additions_dir )
      setup_self ( 'FILESDIR', 'ADDITIONS_DIR' )

      shlib_root = additions_dir + os.sep + 'shlib'

      if os.path.isdir ( shlib_root ):
         shlib_path.append ( shlib_root )

#         if not ROVERLAY_INSTALLED:
         shlib_file = shlib_root + os.sep + SHFUNC_FILENAME
         if os.path.isfile ( shlib_file ):
            setup ( 'FUNCTIONS', shlib_file )
      # -- end if shlib_root;
   # -- end if additions_dir;

   if shlib_path:
      # reversed shlib_path:
      #  assuming that user-provided function files are more important
      #
      setup ( 'SHLIB', ':'.join ( reversed ( shlib_path ) ) )

   # str::exe $EBUILD
   setup_conf ( 'EBUILD', 'TOOLS.EBUILD.exe' )

   # str::exe $GIT_EDITOR = <disable>
   #
   #  It's not that funny if the program waits for user interaction.
   #
   setup ( 'GIT_EDITOR', roverlay.util.sysnop ( False )[0] )

   # str::exe $GIT_ASKPASS copies $GIT_EDITOR
   setup_self ( 'GIT_ASKPASS', 'GIT_EDITOR' )

   # shbool $NOSYNC
   setup ( 'NOSYNC', shbool ( roverlay.config.get_or_fail ( 'nosync' ) ) )

   # shbool $NO_COLOR
   #
   #  stdout/stderr are logged, so colored output should be avoided
   #
   setup ( 'NO_COLOR', SH_TRUE )

   # shbool $DEBUG, $VERBOSE, $QUIET
   if LOGGER.isEnabledFor ( logging.DEBUG ):
      setup ( 'DEBUG',   SH_TRUE  )
      setup ( 'QUIET',   SH_FALSE )
      setup ( 'VERBOSE', SH_TRUE  )
   elif LOGGER.isEnabledFor ( logging.INFO ):
      setup ( 'DEBUG',   SH_FALSE )
      setup ( 'QUIET',   SH_FALSE )
      setup ( 'VERBOSE', SH_TRUE  )
   elif LOGGER.isEnabledFor ( logging.WARNING ):
      setup ( 'DEBUG',   SH_FALSE )
      setup ( 'VERBOSE', SH_FALSE )
      setup ( 'QUIET',   SH_FALSE )
   else:
      setup ( 'DEBUG',   SH_FALSE )
      setup ( 'VERBOSE', SH_FALSE )
      setup ( 'QUIET',   SH_TRUE  )
   # -- end if

   # done
   return env
# --- end of setup_env (...) ---

def get_env ( copy=False ):
   global _SHELL_ENV
   if _SHELL_ENV is None:
      _SHELL_ENV = setup_env()

   if copy:
      return dict ( _SHELL_ENV )
   else:
      return _SHELL_ENV
# --- end of get_env (...) ---

def update_env ( **info ):
   get_env().update ( info )
   return _SHELL_ENV
# --- end of update_env (...) ---


def run_script ( script, phase, return_success=False, logger=None ):
#   global _SHELL_INTPR
#   if _SHELL_INTPR is None:
#      _SHELL_INTPR = roverlay.config.get ( 'SHELL_ENV.shell', '/bin/sh' )

   my_logger = logger or LOGGER
   if phase:
      my_env = get_env ( copy=True )
      my_env ['ROVERLAY_PHASE'] = str ( phase ).lower()
   else:
      # ref
      my_env = get_env()
   # -- end if phase;

   try:
      script_call = subprocess.Popen (
         # ( _SHELL_INTPR, script, ),
         ( script, ),
         stdin      = None,
         stdout     = subprocess.PIPE,
         stderr     = subprocess.PIPE,
         cwd        = my_env ['S'],
         env        = my_env,
      )

      output = script_call.communicate()
   except:
      if 'script_call' in locals():
         try:
            script_call.terminate()
            time.sleep ( 1 )
         finally:
            script_call.kill()
      raise


   log_snip_here = (
      '--- {{}} for script {s!r}, phase {p!r} ---'.format (
         s=script, p=my_env ['ROVERLAY_PHASE']
      )
   )

   # log stdout
   if output[0] and my_logger.isEnabledFor ( logging.INFO ):
      my_logger.info ( log_snip_here.format ( "stdout" ) )
      for line in roverlay.strutil.pipe_lines ( output[0], use_filter=True ):
         my_logger.info ( line )
      my_logger.info ( log_snip_here.format ( "end stdout" ) )
   # -- end if stdout;

   # log stderr
   if output[1] and my_logger.isEnabledFor ( logging.WARNING ):
      my_logger.warning ( log_snip_here.format ( "stderr" ) )
      for line in roverlay.strutil.pipe_lines ( output[1], use_filter=True ):
         my_logger.warning ( line )
      my_logger.warning ( log_snip_here.format ( "end stderr" ) )
   # --- end if stderr;

   if return_success:
      if script_call.returncode == os.EX_OK:
         my_logger.debug ( "script {!r}: success".format ( script ) )
         return True
      else:
         my_logger.warning (
            "script {!r} returned {}".format (
               script, script_call.returncode
            )
         )
         return False
   else:
      return script_call
# --- end of run_script (...) ---
