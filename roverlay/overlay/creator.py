# R overlay -- overlay package, overlay creation
# -*- coding: utf-8 -*-
# Copyright (C) 2012 André Erdmann <dywi@mailerd.de>
# Distributed under the terms of the GNU General Public License;
# either version 2 of the License, or (at your option) any later version.

"""overlay creation

This module provides the OverlayCreator, a class that handles overlay creation,
which is the remote/R package <-> overlay interface (directly used in the
main script).
"""
__all__ = [ 'OverlayCreator', ]

import collections
import time
import logging
import threading
import sys

try:
   import queue
except ImportError:
   # python2
   import Queue as queue


from roverlay                    import config, errorqueue

from roverlay.overlay            import Overlay
from roverlay.overlay.worker     import OverlayWorker
from roverlay.packageinfo        import PackageInfo
from roverlay.packagerules.rules import PackageRules


import roverlay.depres.channels
import roverlay.ebuild.creation
import roverlay.overlay.pkgdir.distroot.static
import roverlay.recipe.distmap
import roverlay.recipe.easyresolver


class PseudoAtomicCounter ( object ):

   def __init__ ( self, start=0, long_int=False ):
      if long_int and sys.version_info < ( 3, 0 ):
         self._value = long ( start )
      else:
         self._value = int ( start )
      self._lock  = threading.Lock()

   def _get_and_inc ( self, step ):
      ret = None
      self._lock.acquire()
      try:
         old_val = self._value
         if step > 0:
            self._value += step
            ret = ( self._value, old_val )
         #elif step < 0: raise...
         else:
            ret = old_val
      finally:
         self._lock.release()

      return ret
   # --- end of _get_and_inc (...) ---

   def inc ( self, step=1 ):
      self._get_and_inc ( step )
   # --- end of inc (...) ---

   def get ( self ):
      return self._get_and_inc ( 0 )
   # --- end of get (...) ---

   def get_nowait ( self ):
      return self._value
   # --- end of get_nowait (...) ---

   def __str__ ( self ):
      return str ( self._value )
   # --- end of __str__ (...) ---


class OverlayCreator ( object ):
   """This is a 'R packages -> Overlay' interface."""

   LOGGER = logging.getLogger ( 'OverlayCreator' )

   def __init__ ( self,
      skip_manifest, incremental, immediate_ebuild_writes,
      logger=None, allow_write=True
   ):
      if logger is None:
         self.logger = self.__class__.LOGGER
      else:
         self.logger = logger.getChild ( 'OverlayCreator' )

      # this queue is used to propagate exceptions from threads
      self._err_queue = errorqueue.ErrorQueue()

      self.rsuggests_flags = set()

      # create distmap and distroot here
      self.distmap  = roverlay.recipe.distmap.setup()
      self.distroot = roverlay.overlay.pkgdir.distroot.static.get_configured()

      time_scan_overlay = time.time()
      # init overlay using config values
      self.overlay = Overlay.new_configured (
         logger              = self.logger,
         incremental         = incremental,
         write_allowed       = allow_write,
         skip_manifest       = skip_manifest,
         runtime_incremental = immediate_ebuild_writes,
         rsuggests_flags     = self.rsuggests_flags,
      )
      time_scan_overlay = time.time() - time_scan_overlay

      self.depresolver = roverlay.recipe.easyresolver.setup ( self._err_queue )
      self.depresolver.make_selfdep_pool ( self.overlay.list_rule_kwargs )

      self.package_rules = PackageRules.get_configured()

      self.NUMTHREADS  = config.get ( 'EBUILD.jobcount', 0 )

      self._pkg_queue  = queue.Queue()
      self._err_queue.attach_queue ( self._pkg_queue, None )


      #self._time_start_run = list()
      #self._time_stop_run  = list()

      self._workers   = None
      self._runlock   = threading.RLock()
      self._work_done = threading.Event()
      self._work_done.set()

      self.closed = False

      # queued packages counter,
      #  package_added != (create_success + create_fail) if a thread hangs
      #  or did not call _pkg_done
      self.package_added  = PseudoAtomicCounter()

      # counts packages that passed ebuild creation
      self.create_success = PseudoAtomicCounter()

      # counts packages that failed ebuild creation
      self.create_fail    = PseudoAtomicCounter()

      # counts packages that passed adding to overlay
      self.overlay_added  = PseudoAtomicCounter()

      self._timestats     = collections.OrderedDict()

      if incremental and time_scan_overlay >= 0.1:
         self._timestats ['scan_overlay'] = time_scan_overlay

      for k in (
         'sync_packages',
         'add_packages',
         'ebuild_creation',
         'overlay_write',
      ):
         self._timestats [k] = -1

   # --- end of __init__ (...) ---

   def set_timestats ( self, name, seconds ):
      self._timestats [name] = seconds
   # --- end of set_timestats (...) ---

   def get_stats ( self ):
      pkg_added   = self.package_added.get_nowait()
      pkg_created = self.create_success.get_nowait()
      pkg_failed  = self.create_fail.get_nowait()
      ov_added    = self.overlay_added.get_nowait()
      ov_failed   = pkg_created - ov_added
      processed   = pkg_created + pkg_failed
      failed      = pkg_failed + ov_failed

      return (
         pkg_added, pkg_created, pkg_failed,
         ov_added, ov_failed,
         processed, failed
      )
   # --- end of get_stats (...) ---

   def stats_str ( self, enclose=True ):
      """Returns a string with some overlay creation stats."""
      def stats_gen():
         """Yields stats strings."""
         stats = self.get_stats()

         # the length of the highest number in stats (^=digit count)
         # max_number_len := { 1,...,5 }
         max_number_len = min ( 5, len ( str ( max ( stats ) ) ) )

         for stats_tuple in zip (
            stats,
            (
               'packages added to the ebuild creation queue',
               'packages passed ebuild creation',
               'packages failed ebuild creation',
               'ebuilds could be added to the overlay',
               'ebuilds couldn\'t be added to the overlay',
               'packages processed in total',
               'packages failed in total',
            ),
         ):
            yield "{num:<{l}} {s}".format (
               num = stats_tuple [0],
               s   = stats_tuple [1],
               l   = max_number_len,
            )

         yield ""

         k_len = min (
            39,
            max ( len ( k ) for k in self._timestats.keys() )
         )

         for k, v in self._timestats.items():
            if v < 0:
               yield "time for {:<{l}} : <unknown>".format ( k, l=k_len, )

            elif v < 1:
               yield "time for {:<{l}} : {} ms".format (
                  k,
                  round ( v * 1000, 2 ),
                  l = k_len,
               )

            elif v > 300:
               yield "time for {:<{l}} : {} minutes".format (
                  k,
                  round ( v / 60., 2 ),
                  l = k_len,
               )

            else:
               yield "time for {}: {} seconds".format ( k, round ( v, 2 ) )
      # --- end of stats_gen (...) ---

      if enclose:
         stats = list ( stats_gen() )

         # maxlen := { 2,...,80 }
         maxlen = 2 + min ( 78,
            len ( max ( stats, key=lambda s : len( s ) ) )
         )

         return (
            "{0:-^{1}}\n".format ( " Overlay creation stats ", maxlen )
            + '\n'.join ( stats )
            #+ '\n{0:-^{1}}'.format ( '', maxlen )
            + '\n' + ( maxlen * '-' )
         )

      else:
         return '\n'.join ( stats_gen() )
   # --- end of stats_str (...) ---

   def _timestamp ( self, description, start, stop=None ):
      """Logs a timestamp, used for testing.

      arguments:
      * description -- timestamp text
      * start       -- when measuring for this timestamp has been started
      * stop        -- stop time; defaults to now (time.time()) if unset
      """
      _stop = time.time() if stop is None else stop
      delta = _stop - start

      self.logger.debug (
         "timestamp: {} (after {:.3f} seconds)".format ( description, delta )
      )
      return delta
   # --- end of _timestamp (...) ---

   def release_package_rules ( self ):
      """Removes all package rules from this object.

      It's safe to call this method after adding all packages.
      """
      del self.package_rules
   # --- end of release_package_rules (...) ---

   def remove_moved_ebuilds ( self, reverse ):
      """See overlay.root.Overlay.remove_moved_ebuilds()."""
      if self.overlay.remove_duplicate_ebuilds ( reverse=reverse ):
         self.depresolver.reload_pools()
   # --- end of remove_moved_ebuilds (...) ---

   def _get_resolver_channel ( self, **channel_kw ):
      """Returns a resolver channel.

      arguments:
      * **channel_kw -- keywords for EbuildJobChannel.__init__
      """
      return self.depresolver.register_channel (
         roverlay.depres.channels.EbuildJobChannel ( **channel_kw )
      )
   # --- end of _get_resolver_channel (...) ---

   def add_package ( self, package_info ):
      """Adds a PackageInfo to the package queue.

      arguments:
      * package_info --
      """
      if self.package_rules.apply_actions ( package_info ):
         if self.overlay.add ( package_info ):
            ejob = roverlay.ebuild.creation.EbuildCreation (
               package_info,
               depres_channel_spawner = self._get_resolver_channel,
               err_queue              = self._err_queue
            )
            self._pkg_queue.put ( ejob )
            # FIXME package_added is now the # of packages queued for creation
            self.package_added.inc()
      # else filtered out
   # --- end of add_package (...) ---

   def write_overlay ( self ):
      """Writes the overlay."""
      if self.overlay.writeable():
         start = time.time()
         self.overlay.write()
         self._timestats ['overlay_write'] = (
            self._timestamp ( "overlay written", start )
         )
      else:
         self.logger.warning ( "Not allowed to write overlay!" )
   # --- end of write_overlay (...) ---

   def show_overlay ( self ):
      """Prints the overlay to the console. Does not create Manifest files."""
      self.overlay.show()
   # --- end of show_overlay (...) ---

   def run ( self, close_when_done=False, max_passno=-1 ):
      """Starts ebuild creation and waits until done."""
      self._runlock.acquire()
      try:
         allow_reraise = True
         t_start = time.time()
         self._work_done.wait()
         self.depresolver.reload_pools()

         self._make_workers ( start_now=False )
         workers    = self._workers
         work_queue = self._pkg_queue

         # run_again <=> bool ( passno == 0 or ejobs )
         ejobs  = list()
         passno = 0
         while ejobs or passno == 0:
            passno         += 1
            ejobs           = list()
            t_passno_start  = time.time()

            if max_passno > -1 and passno > max_passno:
               raise Exception (
                  "max passno ({:d}) reached - aborting".format ( passno )
               )

            self.logger.debug (
               "Running ebuild creation, passno={:d}".format ( passno )
            )

            for worker in workers:
               # assumption: worker not running when calling reset()
               worker.reset()
               worker.start()

            self._waitfor_workers ( do_close=False, delete_workers=False )

            for worker in workers:
               ejobs.extend ( worker.pkg_waiting )


            if ejobs:
               # queue jobs and collect selfdeps
               selfdeps     = list()
               add_selfdeps = selfdeps.extend

               for ejob in ejobs:
                  add_selfdeps ( ejob.selfdeps )
                  add_selfdeps ( ejob.optional_selfdeps )
                  work_queue.put_nowait ( ejob )

               # call selfdep reduction
               self._selfdep_reduction ( selfdeps )


               # running reload_pools() here is correct, but it doesn't
               # have any effect because dependency resolution is done
               # in the first loop run only
               # => "charge" the depresolver with a "should be reloaded" flag
               #self.depresolver.reload_pools()
               self.depresolver.need_reload()

            t_passno_stop = time.time()

            self.logger.info (
               'Ebuild creation #{:d} done after {:.3f}s, '
               'run_again={:s}'.format (
                  passno,
                  ( t_passno_stop - t_passno_start ),
                  ( "yes" if bool ( ejobs ) else "no" )
               )
            )
         # -- end while;

         self.logger.info (
            "Ebuild creation: done after {:d} iteration(s)".format ( passno )
         )

         # done
         for worker in workers:
            if worker.active():
               raise Exception ( "threads should have stopped by now." )
            else:
               self.rsuggests_flags |= worker.rsuggests_flags


         self._workers = None
         del workers

         ##self._timestamp ( "worker threads are done", start )

         # remove broken packages from the overlay (selfdep reduction etc.)
         self.overlay.remove_broken_packages()

         self._timestats ['ebuild_creation'] = (
            self._timestamp ( "run() done", t_start )
         )

         self._work_done.set()
      except ( Exception, KeyboardInterrupt ) as err:
         allow_reraise = False
         self._err_queue.push ( context=-1, error=err )
         raise
      except:
         # just for safety
         allow_reraise = False
         self._err_queue.push ( context=-1, error=None )
         raise
      finally:
         if close_when_done:
            try:
               self.close ( reraise=allow_reraise )
            finally:
               self._runlock.release()
         else:
            self._runlock.release()
   # --- end of run (...) ---

   def _selfdep_reduction ( self, selfdeps ):
      #FIXME move to run()

      #
      # "reduce"
      #
      ## num_removed <- 1
      ##
      ## while num_removed > 0 loop
      ##    num_removed <- 0
      ##
      ##    foreach selfdep in S loop
      ##        num_removed += selfdep.reduce()
      ##    end loop
      ##
      ##    num_removed <- 0
      ## end loop
      ##
      self.overlay.link_selfdeps ( selfdeps )

      num_removed = 1
      num_removed_total = 0

      while num_removed > 0:
         num_removed = 0
         for selfdep in selfdeps:
            num_removed += selfdep.do_reduce()
         num_removed_total += num_removed
      # -- end while num_removed;

      return num_removed_total
   # --- end of _selfdep_reduction (...) ---

   def join ( self ):
      """Waits until ebuild creation is done."""
      self._work_done.wait()
   # --- end of wait (...) ---

   def close ( self, reraise=True ):
      """Closes this OverlayCreator."""
      with self._runlock:
         self._close_workers ( reraise=reraise )
         if self.depresolver is not None:
            self.depresolver.close()
            del self.depresolver
            self.depresolver = None
         self.closed = True
   # --- end of close (...) ---

   def _waitfor_workers ( self, do_close, delete_workers=True, reraise=True ):
      """Waits until the workers are done.

      arguments:
      * do_close -- close (exit) workers if True, else wait until done.
      """

      if self._workers is None: return
      start = None
      self._runlock.acquire()

      try:
         if self._workers is not None:
            if self.NUMTHREADS > 0: start = time.time()

            if do_close:
               self._err_queue.push ( context=-1, error=None )
               for w in self._workers: w.enabled = False
            else:
               for w in self._workers: w.stop_when_empty()

            while True in ( w.active() for w in self._workers ):
               self._pkg_queue.put ( None )

            if delete_workers:
               del self._workers
               self._workers = None

            if reraise:
               for e in self._err_queue.get_exceptions():
                  self.logger.warning ( "Reraising thread exception." )
                  raise e [1]


      except ( Exception, KeyboardInterrupt ) as err:
         # catch interrupt here: still wait until all workers have been closed
         # and reraise after that
#         SIGINT_RESTORE = signal.signal (
#            signal.SIGINT,
#            lambda sig, frame : sys.stderr.write ( "Please wait ...\n" )
#         )

         try:
            self._err_queue.push ( context=-1, error=None )

            while hasattr ( self, '_workers' ) and self._workers is not None:
               if True in ( w.active() for w in self._workers ):
                  self._pkg_queue.put_nowait ( None )
               else:
                  del self._workers
                  self._workers = None
         finally:
#            signal.signal ( signal.SIGINT, SIGINT_RESTORE )
            raise

      finally:
         self._runlock.release()

      return start
   # --- end of _waitfor_workers (...) ---

   def _close_workers ( self, reraise=True ):
      """Tells the workers to exit.
      This is done by disabling them and inserting empty requests (None as
      PackageInfo) to unblock them.
      """
      start = self._waitfor_workers ( True, reraise=reraise )
      if start is not None:
         self._timestamp ( "worker threads are closed", start )
   # --- end of _close_workers (...) ---

   def _pkg_done ( self, ejob ):
      """This is an event method used by worker threads when they have
      processed a package info.

      arguments:
      * package_info --
      """
      package_info = ejob.package_info

      if package_info ['ebuild'] is not None:
         self.create_success.inc()
         if package_info.overlay_package_ref().new_ebuild():
            self.overlay_added.inc()
      else:
         package_info.overlay_package_ref().ebuild_uncreateable ( package_info )
         self.create_fail.inc()

   # --- end of _pkg_done (...) ---

   def _get_worker ( self, start_now=False, use_threads=True ):
      """Creates and returns a worker.

      arguments:
      * start_now   -- if set and True: start the worker immediately
      * use_threads -- if set and False: disable threads
      """
      w = OverlayWorker (
         pkg_queue   = self._pkg_queue,
         logger      = self.logger,
         pkg_done    = self._pkg_done,
         use_threads = use_threads,
         err_queue   = self._err_queue,
      )
      if start_now: w.start()
      return w
   # --- end of _get_worker (...) ---

   def _make_workers ( self, start_now=True ):
      """Creates and starts workers."""
      self._close_workers()
      self._work_done.clear()

      if self.NUMTHREADS > 0:
         start = time.time()
         self.logger.warning (
            "Running in concurrent mode with {num} threads.".format (
               num=self.NUMTHREADS
         ) )
         self._workers = frozenset (
            self._get_worker ( start_now=start_now ) \
               for n in range ( self.NUMTHREADS )
         )
         self._timestamp ( "worker threads initialized", start )
      else:
         self._workers = (
            self._get_worker ( start_now=start_now, use_threads=False ),
         )

   # --- end of _make_workers (...) ---
