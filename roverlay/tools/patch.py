# R overlay -- tools, run patch(1)
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

_PATCHENV = roverlay.util.keepenv (
   ( 'PATH', '' ), 'LANG', 'LC_ALL', 'PWD', 'TMPDIR'
)

_PATCH_CMDV = (
   ( roverlay.config.get_or_fail ( "TOOLS.PATCH.exe" ), )
   + roverlay.config.get_or_fail ( "TOOLS.PATCH.opts" )
)

def dopatch ( filepath, patch, logger ):
   return roverlay.tools.runcmd.run_command (
      cmdv   = ( _PATCH_CMDV + ( filepath, patch ) ),
      env    = _PATCHENV,
      logger = logger
   ).returncode
# --- end of dopatch (...) ---
