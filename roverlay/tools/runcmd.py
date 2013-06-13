# R overlay -- tools, run a command
# -*- coding: utf-8 -*-
# Copyright (C) 2013 André Erdmann <dywi@mailerd.de>
# Distributed under the terms of the GNU General Public License;
# either version 2 of the License, or (at your option) any later version.

import logging
import os
import subprocess

import roverlay.strutil

DEBUG_TO_CONSOLE = False

def run_command ( cmdv, env, logger, return_success=False ):
   if DEBUG_TO_CONSOLE:
      cmd_call = subprocess.Popen ( cmdv, stdin=None, env=env )
   else:
      cmd_call = subprocess.Popen (
         cmdv,
         stdin=None,
         stdout=subprocess.PIPE,
         stderr=subprocess.PIPE,
         env=env,
      )

   output = cmd_call.communicate()

   # log stderr
   if output [1] and logger.isEnabledFor ( logging.WARNING ):
      for line in roverlay.strutil.pipe_lines ( output [1], use_filter=True ):
         logger.warning ( line )

   if return_success:
      return cmd_call.returncode == os.EX_OK
   else:
      return cmd_call
# --- end of run_command (...) ---
