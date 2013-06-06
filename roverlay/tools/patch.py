# R overlay -- tools, run patch(1)
# -*- coding: utf-8 -*-
# Copyright (C) 2013 André Erdmann <dywi@mailerd.de>
# Distributed under the terms of the GNU General Public License;
# either version 2 of the License, or (at your option) any later version.

import subprocess

import roverlay.config
import roverlay.strutil
import roverlay.util

_PATCHENV = roverlay.util.keepenv (
   ( 'PATH', '' ), 'LANG', 'LC_ALL', 'PWD', 'TMPDIR'
)

# NOTE:
#  this module has to be loaded after reading roverlay's config
#

_PATCHOPTS = (
   ( roverlay.config.get_or_fail ( "TOOLS.PATCH.exe" ), )
   + roverlay.config.get_or_fail ( "TOOLS.PATCH.opts" )
)

def dopatch ( filepath, patch, logger ):
   print ( "RUN PATCH", filepath, patch )
   patch_call = subprocess.Popen (
      _PATCHOPTS + (
         filepath, patch
      ),
      stdin=None,
      stdout=subprocess.PIPE,
      stderr=subprocess.PIPE,
      env=_PATCHENV,
   )

   output = patch_call.communicate()

   # log stderr
   for line in roverlay.strutil.pipe_lines ( output [1], use_filter=True ):
      logger.warning ( line )

   return patch_call.returncode
# --- end of dopatch (...) ---
