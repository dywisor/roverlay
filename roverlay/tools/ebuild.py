# R overlay -- tools, run ebuild(1)
# -*- coding: utf-8 -*-
# Copyright (C) 2013 André Erdmann <dywi@mailerd.de>
# Distributed under the terms of the GNU General Public License;
# either version 2 of the License, or (at your option) any later version.

# NOTE:
#  this module has to be loaded after reading roverlay's config
#

import roverlay.tools.runcmd

import roverlay.config
import roverlay.util

_EBUILD_CMDV = (
   roverlay.config.get_or_fail ( 'TOOLS.EBUILD.exe' ),
)

def doebuild (
   ebuild_file, command, logger, env=None, opts=(), return_success=True
):
   logger.debug ( "doebuild: {c}, {e!r}".format ( e=ebuild_file, c=command ) )
   return roverlay.tools.runcmd.run_command (
      cmdv           = ( _EBUILD_CMDV + opts + ( ebuild_file, command ) ),
      env            = env,
      logger         = logger,
      return_success = return_success
   )
# --- end of doebuild (...) ---

def doebuild_manifest (
   ebuild_file, logger, env=None, opts=(), return_success=True
):
   return doebuild (
      ebuild_file    = ebuild_file,
      command        = "manifest",
      logger         = logger,
      env            = env,
      opts           = opts,
      return_success = return_success,
   )
# --- end of doebuild_manifest (...) ---

def doebuild_fetch (
   ebuild_file, logger, env=None, opts=(), return_success=True
):
   return doebuild (
      ebuild_file    = ebuild_file,
      command        = "fetch",
      logger         = logger,
      env            = env,
      opts           = ( '--skip-manifest', ) + opts,
      return_success = return_success,
   )
# --- end of doebuild_fetch (...) ---
