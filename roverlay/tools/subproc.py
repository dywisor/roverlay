# R overlay -- tools, subprocess helpers
# -*- coding: utf-8 -*-
# Copyright (C) 2014 André Erdmann <dywi@mailerd.de>
# Distributed under the terms of the GNU General Public License;
# either version 2 of the License, or (at your option) any later version.

import os
import subprocess
import sys
import time

__all__ = [
   'get_subproc_devnull',
   'subproc_send_term', 'subproc_send_kill',
   'stop_subprocess', 'gracefully_stop_subprocess',
   'create_subprocess', 'run_subprocess'
]

# python >= 3.3 has ProcessLookupError, use more generic exception otherwise
if sys.hexversion >= 0x3030000:
   _ProcessLookupError = ProcessLookupError
else:
   _ProcessLookupError = OSError

# python >= 3.3:
if hasattr ( subprocess, 'DEVNULL' ):
   def get_subproc_devnull(mode=None):
      """Returns a devnull object suitable
      for passing it as stdin/stdout/stderr to subprocess.Popen().

      Python 3.3 and later variant: uses subprocess.DEVNULL

      arguments:
      * mode -- ignored
      """
      return subprocess.DEVNULL
else:
   def get_subproc_devnull(mode='a+'):
      """Returns a devnull object suitable
      for passing it as stdin/stdout/stderr to subprocess.Popen().

      Python 3.2 and earlier variant: opens os.devnull

      arguments:
      * mode -- mode for open(). Defaults to read/append
      """
      return open ( os.devnull, mode )
# --

def _proc_catch_lookup_err ( func ):
   def wrapped ( proc ):
      try:
         func ( proc )
      except _ProcessLookupError:
         return False
      return True

   return wrapped

@_proc_catch_lookup_err
def subproc_send_term ( proc ):
   proc.terminate()

@_proc_catch_lookup_err
def subproc_send_kill ( proc ):
   proc.kill()


def stop_subprocess ( proc, kill_timeout_cs=10 ):
   """Terminates or kills a subprocess created by subprocess.Popen().

   Sends SIGTERM first and sends SIGKILL if the process is still alive after
   the given timeout.

   Returns: None

   arguments:
   * proc            -- subprocess
   * kill_timeout_cs -- max time to wait after terminate() before sending a
                        kill signal (in centiseconds). Should be an int.
                        Defaults to 10 (= 1s).
   """
   if not subproc_send_term ( proc ):
      return

   try:
      for k in range ( kill_timeout_cs ):
         if proc.poll() is not None:
            return
         time.sleep ( 0.1 )
   except:
      subproc_send_kill ( proc )
   else:
      subproc_send_kill ( proc )
# --- end of stop_subprocess (...) ---

def gracefully_stop_subprocess ( proc, **kill_kwargs ):
   try:
      if subproc_send_term ( proc ):
         proc.communicate()
   except:
      stop_subprocess ( proc, **kill_kwargs )
      raise

def create_subprocess ( cmdv, **kwargs ):
   """subprocess.Popen() wrapper that redirects stdin/stdout/stderr to
   devnull or to a pipe if set to False/True.

   Returns: subprocess

   arguments:
   * cmdv     --
   * **kwargs --
   """
   devnull_obj = None

   for key in { 'stdin', 'stdout', 'stderr' }:
      if key not in kwargs:
         pass
      elif kwargs [key] is True:
         kwargs [key] = subprocess.PIPE

      elif kwargs [key] is False:
         if devnull_obj is None:
            devnull_obj = get_subproc_devnull()
            assert devnull_obj is not None

         kwargs [key] = devnull_obj
      # else don't care
   # --

   return subprocess.Popen ( cmdv, **kwargs )
# --- end of create_subprocess (...) ---

def run_subprocess ( cmdv, kill_timeout_cs=10, **kwargs ):
   """Calls create_subprocess() and waits for the process to exit.
   Catches exceptions and terminates/kills the process in that case

   Returns: 2-tuple ( subprocess, output )

   arguments:
   * cmdv            --
   * kill_timeout_cs -- time to wait after SIGTERM before sending SIGKILL
                        (in centiseconds), see stop_subprocess() for details
                        Defaults to 10.
   * **kwargs        --
   """
   proc = None
   try:
      proc   = create_subprocess ( cmdv, **kwargs )
      output = proc.communicate()
   except:
      if proc is not None:
         stop_subprocess ( proc, kill_timeout_cs=kill_timeout_cs )
      raise

   return ( proc, output )
# --- end of run_subprocess (...) ---
