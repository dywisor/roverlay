# R overlay -- tools, run a command
# -*- coding: utf-8 -*-
# Copyright (C) 2013 André Erdmann <dywi@mailerd.de>
# Distributed under the terms of the GNU General Public License;
# either version 2 of the License, or (at your option) any later version.

import logging
import os
import subprocess

import roverlay.strutil
import roverlay.tools.subproc
from roverlay.tools.subproc import run_subprocess as _run_subprocess

DEBUG_TO_CONSOLE = False

def run_command_get_output (
   cmdv, env, debug_to_console=False, use_filter=True, filter_func=None,
   binary_stdout=False, stdin=None
):
   # note that debug_to_console breaks calls that want to parse stdout
   pipe_target = None if debug_to_console else subprocess.PIPE

   cmd_call, raw_output = _run_subprocess (
      cmdv, stdin=stdin, stdout=pipe_target, stderr=pipe_target, env=env
   )

   if binary_stdout:
      assert len ( raw_output ) == 2
      output = [
         raw_output[0],
         list ( roverlay.strutil.pipe_lines (
            raw_output[1], use_filter=use_filter, filter_func=filter_func
         ) )
      ]
   else:
      output = [
         (
            list ( roverlay.strutil.pipe_lines (
               stream, use_filter=use_filter, filter_func=filter_func
            ) )
            if stream is not None else None
         ) for stream in raw_output
      ]

   return ( cmd_call, output )
# --- end of run_command_get_output (...) ---

def run_command ( cmdv, env, logger, return_success=False ):
   cmd_call, output = run_command_get_output (
      cmdv, env, DEBUG_TO_CONSOLE, use_filter=True
   )

   # log stderr
   if output[1] and logger.isEnabledFor ( logging.WARNING ):
      for line in output[1]:
         logger.warning ( line )

   if return_success:
      return cmd_call.returncode == os.EX_OK
   else:
      return cmd_call
# --- end of run_command (...) ---
