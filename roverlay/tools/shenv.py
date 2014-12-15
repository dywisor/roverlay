# R overlay -- tools, shell script environment
# -*- coding: utf-8 -*-
# Copyright (C) 2013 André Erdmann <dywi@mailerd.de>
# Distributed under the terms of the GNU General Public License;
# either version 2 of the License, or (at your option) any later version.

import fnmatch
import logging
import os
import sys
import subprocess
import tempfile
import time


import roverlay.config
import roverlay.strutil
import roverlay.util
import roverlay.stats.collector
import roverlay.tools.subproc
from roverlay.tools.subproc import run_subprocess as _run_subprocess


# _SHELL_ENV, _SHELL_INTPR are created when calling run_script()
#
_SHELL_ENV   = None
#_SHELL_INTPR = None
LOGGER       = logging.getLogger ( 'shenv' )

NULL_PHASE = 'null'

SHENV_VARS_TO_KEEP = frozenset ({
   ( 'PATH', '/usr/local/bin:/usr/bin:/bin' ),
   'PWD',
   'LOGNAME',
   'SHLVL',
   'TERM',
   'HOME',
   'LANG',
})

SHENV_WILDCARD_VARS_TO_KEEP = frozenset ({ 'LC_?*', })


# shell env dict quickref: see doc/rst/usage.rst

# @typedef shbool is SH_TRUE|SH_FALSE, where:
SH_TRUE  = 'y'
SH_FALSE = 'n'

def shbool ( value, flip=False ):
   """Converts value into a shbool."""
   # SH_TRUE := value XOR invert
   # -> SH_FALSE := value <=> invert
   return SH_FALSE if bool ( value ) is bool ( flip ) else SH_TRUE
# --- end of shbool (...) ---

def get_shbool ( value, empty_is_false=True, undef_is_false=True ):
   """Converts a string into a shbool."""
   if not value:
      return SH_FALSE if empty_is_false else SH_TRUE
   elif value in { SH_TRUE, SH_FALSE }:
      return value
   elif value.lower() in { 'yes', 'on', '1', 'enabled', 'true' }:
      return SH_TRUE
   elif undef_is_false:
      return SH_FALSE
   elif value.lower() in { 'no', 'off', '0', 'disabled', 'false' }:
      return SH_FALSE
   else:
      return SH_TRUE
# --- end of get_shbool (...) ---


def setup_env():
   """Returns a 'well-defined' env dict for running scripts."""

   _fnmatch           = fnmatch.fnmatch
   ROVERLAY_INSTALLED = roverlay.config.get_or_fail ( 'installed' )
   SHLIB_DIRNAME      = 'shlib'
   SHFUNC_FILENAME    = 'functions.sh'

   # import os.environ
   if roverlay.config.get ( "SHELL_ENV.filter_env", True ):
      # (keepenv does not support wildcars)
      env = roverlay.util.keepenv_v ( SHENV_VARS_TO_KEEP )

      for varname, value in os.environ.items():
         if any (
            _fnmatch ( varname, pattern )
            for pattern in SHENV_WILDCARD_VARS_TO_KEEP
         ):
            env [varname] = value

      # what else?
      #
      # GIT_AUTHOR_NAME, GIT_AUTHOR_EMAIL, GIT_COMMITTER_NAME,
      # GIT_COMMITTER_EMAIL, ... are set in the hookrc file
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

   def setup_conf_optional ( k, c, fallback=None ):
      value = roverlay.config.get ( c )
      if value is not None:
         env [k] = value
         return True
      elif fallback is not None:
         env [k] = str ( fallback )
         return False
      else:
         return None
   # --- end of setup_conf_optional (...) ---

   def setup_self ( k, c ):
      env[k] = env[c]

   ## create shell vars

   # str::dirpath $PORTDIR
   setup_conf_optional ( 'PORTDIR', 'portdir' )

   # str::filepath $ROVERLAY_HOOKRC (optional)
   setup_conf_optional ( 'ROVERLAY_HOOKRC', 'EVENT_HOOK.config_file' )

   # str::filepath $ROVERLAY_EXE
   setup ( 'ROVERLAY_HELPER_EXE', sys.argv[0] )
   roverlay_exe = ( os.path.dirname ( sys.argv[0] ) + os.sep + 'roverlay' )
   if os.path.isfile ( roverlay_exe + '.py' ):
      setup ( 'ROVERLAY_EXE', roverlay_exe + '.py' )
   else:
      setup ( 'ROVERLAY_EXE', roverlay_exe )

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

   # str::dirpath $WORKDIR
   setup_conf ( 'WORKDIR', 'CACHEDIR.root' )

   # str::filepath $STATS_DB (optional)
   setup_conf_optional ( 'STATS_DB', 'STATS.dbfile' )

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
      data_root = roverlay.config.get_or_fail ( 'INSTALLINFO.libexec' )
      setup ( 'DATADIR', data_root )
      installed_shlib = data_root + os.sep + SHLIB_DIRNAME

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
   sync_in_hooks = roverlay.config.get ( 'sync_in_hooks', None )
   if sync_in_hooks is None:
      setup ( 'NOSYNC', shbool ( roverlay.config.get_or_fail ( 'nosync' ) ) )
   else:
      setup ( 'NOSYNC', shbool ( not sync_in_hooks ) )

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

def make_env ( copy=False ):
   global _SHELL_ENV
   if _SHELL_ENV is None:
      _SHELL_ENV = setup_env()

   if copy:
      return dict ( _SHELL_ENV )
   else:
      return _SHELL_ENV
# --- end of make_env (...) ---

def update_env ( **info ):
   env = make_env()
   env.update ( info )
   return env
# --- end of update_env (...) ---

def get_env ( phase, copy=True ):
   env = make_env ( copy=copy )
   if phase:
      env ['ROVERLAY_PHASE'] = str ( phase ).lower()

   env ['HAS_CHANGES'] = shbool (
      roverlay.stats.collector.static.overlay_has_any_changes()
   )

   return env
# --- end of get_env (...) ---

def restore_msg_vars ( env ):
   shbool_from_env = (
      lambda k, x, **kw: get_shbool ( os.environ.get ( k, x ), **kw )
   )

   # restore DEBUG/VERBOSE/QUIET
   env ['DEBUG']   = shbool_from_env ( 'DEBUG',   SH_FALSE )
   env ['VERBOSE'] = shbool_from_env ( 'VERBOSE', SH_TRUE  )
   env ['QUIET']   = shbool_from_env ( 'QUIET',   SH_FALSE )

   # reset NO_COLOR
   env ['NO_COLOR'] = shbool_from_env (
      'NO_COLOR', SH_TRUE, empty_is_false=False
   )
   return None
# --- end of restore_msg_vars (...) ---

def run_script_exec (
   script, phase, argv=(), initial_dir=None, use_path=True, extra_env=None,
):
   my_env = get_env ( phase )
   restore_msg_vars ( my_env )

   if extra_env:
      my_env.update ( extra_env )

   if initial_dir:
      os.chdir ( initial_dir )

   if use_path:
      os.execvpe ( script, argv, my_env )
   else:
      os.execve ( script, argv, my_env )
   raise Exception ( "exec? (unreachable code)" )
# --- end of run_script_exec (...) ---


def run_script (
   script, phase, argv=(), return_success=False, logger=None,
   log_output=True, initial_dir=None, allow_stdin=True
):
#   global _SHELL_INTPR
#   if _SHELL_INTPR is None:
#      _SHELL_INTPR = roverlay.config.get ( 'SHELL_ENV.shell', '/bin/sh' )

   my_logger = logger or LOGGER
   my_env    = get_env ( phase )

   script_call, output = _run_subprocess (
      # ( _SHELL_INTPR, script, ),
      ( script, ) + argv,
      stdin      = None if allow_stdin else False,
      stdout     = subprocess.PIPE if log_output else None,
      stderr     = subprocess.PIPE if log_output else None,
      cwd        = my_env ['S'] if initial_dir is None else initial_dir,
      env        = my_env,
   )

   if log_output:
      log_snip_here = (
         '--- {{}} for script {s!r}, phase {p!r} ---'.format (
            s=script, p=my_env ['ROVERLAY_PHASE']
         )
      )

      # log stdout
      if output[0] and my_logger.isEnabledFor ( logging.INFO ):
         my_logger.info ( log_snip_here.format ( "stdout" ) )
         for line in (
            roverlay.strutil.pipe_lines ( output[0], use_filter=True )
         ):
            my_logger.info ( line )
         my_logger.info ( log_snip_here.format ( "end stdout" ) )
      # -- end if stdout;

      # log stderr
      if output[1] and my_logger.isEnabledFor ( logging.WARNING ):
         my_logger.warning ( log_snip_here.format ( "stderr" ) )
         for line in (
            roverlay.strutil.pipe_lines ( output[1], use_filter=True )
         ):
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
