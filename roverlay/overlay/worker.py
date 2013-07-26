# R overlay -- overlay package, R package -> overlay work module
# -*- coding: utf-8 -*-
# Copyright (C) 2012 André Erdmann <dywi@mailerd.de>
# Distributed under the terms of the GNU General Public License;
# either version 2 of the License, or (at your option) any later version.

"""overlay worker

This module provides OverlayWorker, a class that handles threaded ebuild
creation for PackageInfo instances.
"""

__all__ = [ 'OverlayWorker', ]

import sys
import threading

from roverlay.depres.channels    import EbuildJobChannel
from roverlay.ebuild.creation    import EbuildCreation

# this controls whether debug message from OverlayWorker.run() are printed
# to stderr or suppressed
DEBUG = True

class OverlayWorker ( object ):
   """Overlay package queue worker."""

   def __init__ ( self, pkg_queue, logger, use_threads, err_queue, stats ):
      """Initializes a worker.

      arguments:
      * pkg_queue   -- queue with PackageInfos
      * depresolver -- dependency resolver to use
      * logger      -- logger to use
      * use_threads -- whether to run this worker as a thread or not
      * err_queue   --
      * stats       --
      """
      self.logger      = logger
      self.pkg_queue   = pkg_queue

      self.err_queue   = err_queue
      self.stats       = stats

      self._use_thread = use_threads
      self._thread     = None
      self.running     = False
      self.enabled     = True
      self.halting     = False

      self.pkg_waiting = list()

      self.rsuggests_flags = set()
   # --- end of __init__ (...) ---

   def reset ( self ):
      self.pkg_waiting = list()
      self.running     = False
      self.halting     = False
      self.enabled     = True
   # --- end of reset (...) ---

   def start ( self ):
      """Starts the worker."""
      if self._thread is not None:
         self._thread.join()
         del self._thread

      self.enabled = True
      if self._use_thread:
         self._thread = threading.Thread ( target=self._run )
         self._thread.start()
      else:
         self._run_nothread()
   # --- end of start (...) ---

   def stop_when_empty ( self ):
      """Tells the worker thread to exit when the queue is empty."""
      self.enabled = False
      self.halting = True
   # --- end of stop_when_empty (...) ---

   def active ( self ):
      """Returns True if this worker is active (running or enabled)."""
      return self.running or self.enabled
   # --- end of active (...) ---

   def _process ( self, ejob ):
      """Processes a PackageInfo taken from the queue.

      arguments:
      * ejob --
      """
      p_info = ejob.package_info
      ejob.run ( self.stats )

      if ejob.busy():
         self.pkg_waiting.append ( ejob )
      elif p_info.get ( 'ebuild' ) is None:
         # no ebuild created
         self.stats.pkg_processed.inc()
         p_info.overlay_package_ref().ebuild_uncreateable ( p_info )
         self.stats.pkg_fail.inc()
      else:
         # ebuild created
         #  if new_ebuild() returns False: ebuild could not be written
         self.stats.pkg_processed.inc()
         p_info.overlay_package_ref().new_ebuild()

         if hasattr ( ejob, 'use_expand_flag_names' ):
            self.rsuggests_flags |= ejob.use_expand_flag_names

         self.stats.pkg_success.inc()
   # --- end of _process (...) ---

   def _run ( self ):
      """Runs the worker (thread mode)."""

      if DEBUG:
         def debug ( msg ):
            sys.stderr.write (
               "0x{:x} WORKER: {}\n".format ( id ( self ), msg )
            )
      else:
         debug = lambda k: None

      try:
         self.running = True
         self.halting = False
         while ( self.enabled or (
               self.halting and not self.pkg_queue.empty()
            ) and \
            self.err_queue.empty
         ):
            debug ( "WAITING" )
            p = self.pkg_queue.get()
            debug ( "RECEIVED A TASK, " + str ( p ) )

            # drop empty requests that are used to unblock get()
            if p is not None and self.err_queue.empty:
               debug ( "ENTER PROC" )
               self._process ( p )
            elif self.halting:
               # receiving an empty request while halting means 'stop now',
               self.enabled = False
               self.halting = False

            self.pkg_queue.task_done()

         debug ( "STOPPING - DONE" )
      except ( Exception, KeyboardInterrupt ) as e:
         self.logger.exception ( e )
         self.err_queue.push ( id ( self ), e )

         self.enabled = False
         self.halting = False
      except:
         self.enabled = False
         self.halting = False
         raise
      finally:
         self.running = False

   # --- end of run (...) ---

   def _run_nothread ( self ):
      """Runs the worker (no-thread mode)."""
      try:
         self.running = True
         while self.enabled and not self.pkg_queue.empty():

            p = self.pkg_queue.get_nowait()

            # drop empty requests that are used to unblock get()
            if p is not None:
               self._process ( p )

            self.pkg_queue.task_done()
      except:
         self.enabled = False
         self.halting = False
         raise
      finally:
         self.running = False
   # --- end of _run_nothread (...) ---
