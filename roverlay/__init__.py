# R overlay -- roverlay package (__init__)
# -*- coding: utf-8 -*-
# Copyright (C) 2012, 2013 André Erdmann <dywi@mailerd.de>
# Distributed under the terms of the GNU General Public License;
# either version 2 of the License, or (at your option) any later version.

"""R overlay package

Provides roverlay initialization helpers (setup_initial_logger,
load_config_file) and some information vars (version, name, ...).
"""

__all__ = [ 'setup_initial_logger', 'load_config_file', ]

name        = "R_overlay"
version     = "0.2.5"

description_str = "R overlay creation (roverlay) " + version
license_str=(
   'Copyright (C) 2012, 2013 Andr\xc3\xa9 Erdmann\n'
   'Distributed under the terms of the GNU General Public License;\n'
   'either version 2 of the License, or (at your option) any later version.\n'
)

import roverlay.config
import roverlay.recipe.easylogger


def setup_initial_logger():
   """Sets up initial logging."""
   roverlay.recipe.easylogger.setup_initial()

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

   if not load_main_only:
      confloader.load_field_definition (
         roverlay_config.get_or_fail ( "DESCRIPTION.field_definition_file" )
      )

      confloader.load_use_expand_map (
         roverlay_config.get ( "EBUILD.USE_EXPAND.rename_file" )
      )

   return roverlay_config
