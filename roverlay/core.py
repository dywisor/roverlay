# R overlay -- roverlay package, core functions
# -*- coding: utf-8 -*-
# Copyright (C) 2012, 2013 André Erdmann <dywi@mailerd.de>
# Distributed under the terms of the GNU General Public License;
# either version 2 of the License, or (at your option) any later version.

"""R overlay package

Provides roverlay initialization helpers (setup_initial_logger,
load_config_file) and some information vars (version, name, ...).
"""

__all__ = [
   'DIE', 'die', 'setup_initial_logger', 'load_config_file',
   'locate_config_file', 'default_helper_setup', 'load_locate_config_file',
]

import os
import sys
import logging

import roverlay.config
import roverlay.recipe.easylogger
import roverlay.tools.shenv


name        = "R_overlay"
version     = "0.2.6"

description_str = "R overlay creation (roverlay) " + version
license_str     = (
   'Copyright (C) 2012, 2013 Andr\xe9 Erdmann\n'
   'Distributed under the terms of the GNU General Public License;\n'
   'either version 2 of the License, or (at your option) any later version.\n'
)

DEFAULT_CONFIG_FILE_NAME = "R-overlay.conf"

# directories where the config file could be found if roverlay has been
# installed, in order:
# * user roverlay dir (${HOME}/roverlay)
# * system config dir /etc/roverlay
#
# Note: $PWD has been removed
#
CONFIG_DIRS = tuple ((
   (
      ( os.getenv ( 'HOME' ) or os.path.expanduser ( '~' ) )
      + os.sep + 'roverlay'
   ),
   # os.sep is '/' if /etc exists, so don't care about that
   '/etc/roverlay',
))

class DIE ( object ):
   """Container class for various system exit 'events'."""
   NOP          =  os.EX_OK
   ERR          =  1
   BAD_USAGE    =  os.EX_USAGE
   USAGE        =  os.EX_USAGE
   ARG          =  9
   CONFIG       =  os.EX_CONFIG
   OV_CREATE    =  20
   SYNC         =  30
   CMD_LEFTOVER =  90
   IMPORT       =  91
   UNKNOWN      =  95
   INTERRUPT    = 130

   @staticmethod
   def die ( msg=None, code=None ):
      """
      Calls syst.exit (code:=DIE.ERR) after printing a message (if any).
      """
      code = DIE.ERR if code is None else code
      if msg is not None:
         sys.stderr.write ( msg + "\n" )
#      else:
#         sys.stderr.write ( "died.\n" )
      sys.exit ( code )
   # --- end of die (...) ---

# --- DIE: exit codes ---
die = DIE.die


def setup_initial_logger():
   """Sets up initial logging."""
   roverlay.recipe.easylogger.setup_initial()
# --- end of setup_initial_logger (...) ---

def force_console_logging ( *args, **kwargs ):
   return roverlay.recipe.easylogger.force_console_logging ( *args, **kwargs )
# --- end of force_console_logging (...) ---

def load_config_file (
   cfile, extraconf=None, setup_logger=True, load_main_only=False
):
   """
   Loads the config, including the field definition file.
   Sets up the logger afterwards.
   (Don't call this method more than once.)

   arguments:
   * cfile          -- path to the config file
   * extraconf      -- a dict with additional config entries that will override
                        entries read from cfile
   * setup_logger   -- set up logger (defaults to True)
   * load_main_only -- if set and True: load main config file only
                        (= do not load field def, ...)
   """
   roverlay_config = roverlay.config.access()

   confloader = roverlay_config.get_loader()

   if cfile:
      confloader.load_config ( cfile )

   if extraconf is not None:
      roverlay_config.merge_with ( extraconf )

   if setup_logger:
      roverlay.recipe.easylogger.setup ( roverlay_config )
      logging.getLogger().debug ( "roverlay version " + version )

   if not load_main_only:
      confloader.load_field_definition (
         roverlay_config.get_or_fail ( "DESCRIPTION.field_definition_file" )
      )

      confloader.load_use_expand_map (
         roverlay_config.get ( "EBUILD.USE_EXPAND.rename_file" )
      )

   return roverlay_config

# --- end of load_config_file (...) ---

def locate_config_file (
   ROVERLAY_INSTALLED, CONFIG_FILE_NAME=DEFAULT_CONFIG_FILE_NAME
):
   # search for the config file if roverlay has been installed
   if ROVERLAY_INSTALLED:
      cfg        = None
      config_dir = None

      for config_dir in CONFIG_DIRS:
         cfg = config_dir + os.sep + CONFIG_FILE_NAME
         if os.path.isfile ( cfg ):
            return cfg

   elif os.path.exists ( CONFIG_FILE_NAME + '.local' ):
      return CONFIG_FILE_NAME + '.local'

   elif os.path.exists ( CONFIG_FILE_NAME ):
      return CONFIG_FILE_NAME

   return None
# --- end of locate_config_file (...) ---

def load_locate_config_file (
   ROVERLAY_INSTALLED, CONFIG_FILE_NAME=DEFAULT_CONFIG_FILE_NAME, **kw
):
   return load_config_file (
      locate_config_file ( ROVERLAY_INSTALLED, CONFIG_FILE_NAME ), **kw
   )
# --- end of load_locate_config_file (...) ---

def default_helper_setup ( ROVERLAY_INSTALLED, log_to_console=True ):
   if log_to_console is True:
      roverlay.recipe.easylogger.force_console_logging (
         log_level=logging.WARNING
      )
   elif log_to_console or log_to_console == 0:
      roverlay.recipe.easylogger.force_console_logging (
         log_level=log_to_console
      )
   else:
      setup_initial_logger()

   config = load_locate_config_file (
      ROVERLAY_INSTALLED, extraconf={ 'installed': ROVERLAY_INSTALLED, },
      setup_logger=False, load_main_only=True,
   )

   roverlay.tools.shenv.setup_env()
   return config
# --- end of default_helper_setup (...) ---
