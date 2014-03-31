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
import logging
import threading
import sys

try:
   import queue
except ImportError:
   # python2
   import Queue as queue


from roverlay                    import config, errorqueue

from roverlay.overlay.root       import Overlay
from roverlay.overlay.worker     import OverlayWorker
from roverlay.packageinfo        import PackageInfo
from roverlay.packagerules.rules import PackageRules


import roverlay.depres.channels
import roverlay.ebuild.creation
import roverlay.overlay.rulegen
import roverlay.overlay.pkgdir.distroot.static
import roverlay.recipe.distmap
import roverlay.recipe.easyresolver
import roverlay.stats.collector
import roverlay.util.hashpool

class OverlayCreator ( object ):
   """This is a 'R packages -> Overlay' interface."""

   LOGGER = logging.getLogger ( 'OverlayCreator' )
   STATS  = roverlay.stats.collector.static.overlay_creation

   HASHPOOL_WORKER_COUNT = 0

   def __init__ ( self,
      skip_manifest, incremental, immediate_ebuild_writes,
      logger=None, allow_write=True, greedy_depres=True, repo_id_map=None,
   ):
      if logger is None:
         self.logger = self.__class__.LOGGER
      else:
         self.logger = logger.getChild ( self.__class__.__name__ )

      # this queue is used to propagate exceptions from threads
      self._err_queue = errorqueue.ErrorQueue()
      self.stats      = self.__class__.STATS

      self.rsuggests_flags = set()

      # create distmap and distroot here
      self.distmap  = roverlay.recipe.distmap.setup()
      self.distroot = roverlay.overlay.pkgdir.distroot.static.get_configured()

      # init overlay using config values
      self.overlay = Overlay.new_configured (
         logger              = self.logger,
         incremental         = incremental,
         write_allowed       = allow_write,
         skip_manifest       = skip_manifest,
         runtime_incremental = immediate_ebuild_writes,
         rsuggests_flags     = self.rsuggests_flags,
      )

      self.depresolver = roverlay.recipe.easyresolver.setup ( self._err_queue )
      self.depresolver.make_selfdep_pool (
         roverlay.overlay.rulegen.DepresRuleGenerator (
            self.overlay, repo_id_map=repo_id_map
         )
      )

      if greedy_depres:
         self._depres_channel_cls = roverlay.depres.channels.EbuildJobChannel
      else:
         self._depres_channel_cls = (
            roverlay.depres.channels.NonGreedyDepresChannel
         )

      self.package_rules = PackageRules.get_configured()

      self.NUMTHREADS  = config.get ( 'EBUILD.jobcount', 0 )

      self._pkg_queue           = queue.Queue()
      self._pkg_queue_postponed = list()
      self._err_queue.attach_queue ( self._pkg_queue, None )

      self._workers   = None
      self._runlock   = threading.RLock()
      self._work_done = threading.Event()
      self._work_done.set()

      self.closed = False

   # --- end of __init__ (...) ---

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
         self._depres_channel_cls ( **channel_kw )
      )
   # --- end of _get_resolver_channel (...) ---

   def add_package ( self, package_info, allow_postpone=True ):
      """Adds a PackageInfo to the package queue.

      arguments:
      * package_info --
      """
      if self.package_rules.apply_actions ( package_info ):
         add_result = self.overlay.add (
            package_info, allow_postpone=allow_postpone
         )

         if add_result is True:
            ejob = roverlay.ebuild.creation.EbuildCreation (
               package_info,
               depres_channel_spawner = self._get_resolver_channel,
               err_queue              = self._err_queue
            )
            self._pkg_queue.put ( ejob )
            self.stats.pkg_queued.inc()

         elif add_result is False:
            self.stats.pkg_dropped.inc()

         elif allow_postpone:
            self.stats.pkg_queue_postponed.inc()
            self._pkg_queue_postponed.append ( ( package_info, add_result ) )

         else:
            raise Exception ( "bad return from overlay.add()" )

      else:
         # else filtered out
         self.stats.pkg_filtered.inc()
   # --- end of add_package (...) ---

   def discard_postponed ( self ):
      self._pkg_queue_postponed [:] = []
   # --- end of discard_postponed (...) ---

   def enqueue_postponed ( self, prehash_manifest=False ):
      # !!! prehash_manifest results in threaded calculation taking
      #     _more_ time than single-threaded. Postponed packages usually
      #     don't need a revbump, so the time penalty here likely does
      #     not outweigh the benefits (i.e. no need to recalculate on revbump)
      #

      if self._pkg_queue_postponed:
         qtime = self.stats.queue_postponed_time

         self.logger.info ( "Checking for packages that need a revbump" )

         if self.HASHPOOL_WORKER_COUNT < 1:
            pass

         elif roverlay.util.hashpool.HAVE_CONCURRENT_FUTURES:
            qtime.begin ( "setup_hashpool" )

            # determine hashes that should be calculated here
            if prehash_manifest:
               # * calculate all hashes, not just the distmap one
               # * assuming that all package dirs are of the same class/type
               #
               distmap_hash = PackageInfo.DISTMAP_DIGEST_TYPE
               extra_hashes = self._pkg_queue_postponed[0][1]().HASH_TYPES

               if not extra_hashes:
                  hashes = { distmap_hash, }
               elif distmap_hash in extra_hashes:
                  hashes = extra_hashes
               else:
                  hashes = extra_hashes | { distmap_hash, }
            else:
               hashes = { PackageInfo.DISTMAP_DIGEST_TYPE, }

            my_hashpool = roverlay.util.hashpool.HashPool (
               hashes, self.HASHPOOL_WORKER_COUNT
            )

            for p_info, pkgdir_ref in self._pkg_queue_postponed:
               my_hashpool.add (
                  id ( p_info ),
                  p_info.get ( "package_file" ), p_info.hashdict
               )

            qtime.end ( "setup_hashpool" )

            qtime.begin ( "make_hashes" )
            my_hashpool.run()
            qtime.end ( "make_hashes" )
         else:
            self.logger.warning (
               "enqueue_postponed(): falling back to single-threaded variant."
            )
         # -- end if HAVE_CONCURRENT_FUTURES

         qtime.begin ( "queue_packages" )
         for p_info, pkgdir_ref in self._pkg_queue_postponed:
            add_result = pkgdir_ref().add ( p_info, allow_postpone=False )

            if add_result is True:
               ejob = roverlay.ebuild.creation.EbuildCreation (
                  p_info,
                  depres_channel_spawner = self._get_resolver_channel,
                  err_queue              = self._err_queue
               )
               self._pkg_queue.put ( ejob )
               self.stats.pkg_queued.inc()

            elif add_result is False:
               self.stats.pkg_dropped.inc()

            else:
               raise Exception (
                  "enqueue_postponed() should not postpone packages further."
               )
         # -- end for
         qtime.end ( "queue_packages" )

         # clear list
         self._pkg_queue_postponed[:] = []
   # --- end of enqueue_postponed (...) ---

   def write_overlay ( self ):
      """Writes the overlay."""
      if self.overlay.writeable():
         self.overlay.write()
         # debug message here as it's already logged by the overlay
         self.logger.debug ( "overlay written" )
      else:
         self.logger.warning ( "Not allowed to write overlay!" )
   # --- end of write_overlay (...) ---

   def show_overlay ( self ):
      """Prints the overlay to the console. Does not create Manifest files."""
      self.overlay.show()
      sys.stdout.flush()
      sys.stderr.flush()
   # --- end of show_overlay (...) ---

   def run ( self, close_when_done=False, max_passno=-1 ):
      """Starts ebuild creation and waits until done."""
      self._runlock.acquire()
      self.stats.creation_time.begin ( "setup" )
      allow_reraise = True
      try:
         self._work_done.wait()
         self.depresolver.reload_pools()

         self._make_workers ( start_now=False )
         workers    = self._workers
         work_queue = self._pkg_queue

         # run_again <=> bool ( passno == 0 or ejobs )
         ejobs  = list()
         passno = 0
         self.stats.creation_time.end ( "setup" )
         while ejobs or passno == 0:
            passno         += 1
            ejobs           = list()
            passno_str      = "iteration_" + str ( passno )

            self.stats.creation_time.begin ( passno_str )

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

            passno_time = self.stats.creation_time.end ( passno_str )

            self.logger.info (
               'Ebuild creation #{:d} done, run_again={:s}'.format (
                  passno, ( "yes" if bool ( ejobs ) else "no" )
               )
            )
         # -- end while;

         self.stats.creation_time.begin ( "finalize" )

         self.logger.info (
            "Ebuild creation: done after {:d} iteration(s)".format ( passno )
         )

         # done
         for worker in workers:
            if worker.active():
               raise Exception ( "threads should have stopped by now." )
            else:
               self.rsuggests_flags |= worker.rsuggests_flags
               self.stats.merge_with ( worker.stats )


         self._workers = None
         del workers

         # remove broken packages from the overlay (selfdep reduction etc.)
         self.overlay.remove_broken_packages()

         self.stats.creation_time.end ( "finalize" )
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
      self._runlock.acquire()

      try:
         if self._workers is not None:

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

      return None
   # --- end of _waitfor_workers (...) ---

   def _close_workers ( self, reraise=True ):
      """Tells the workers to exit.
      This is done by disabling them and inserting empty requests (None as
      PackageInfo) to unblock them.
      """
      self._waitfor_workers ( True, reraise=reraise )
      self.logger.debug ( "worker threads have been closed" )
   # --- end of _close_workers (...) ---

   def _get_worker ( self, start_now=False, use_threads=True ):
      """Creates and returns a worker.

      arguments:
      * start_now   -- if set and True: start the worker immediately
      * use_threads -- if set and False: disable threads
      """
      w = OverlayWorker (
         pkg_queue   = self._pkg_queue,
         logger      = self.logger,
         use_threads = use_threads,
         err_queue   = self._err_queue,
         stats       = self.stats.get_new(),
      )
      if start_now: w.start()
      return w
   # --- end of _get_worker (...) ---

   def _make_workers ( self, start_now=True ):
      """Creates and starts workers."""
      self._close_workers()
      self._work_done.clear()

      if self.NUMTHREADS > 0:
         self.logger.warning (
            "Running in concurrent mode with {num} threads.".format (
               num=self.NUMTHREADS
         ) )
         self._workers = frozenset (
            self._get_worker ( start_now=start_now ) \
               for n in range ( self.NUMTHREADS )
         )
         self.logger.debug ( "worker threads initialized" )
      else:
         self._workers = (
            self._get_worker ( start_now=start_now, use_threads=False ),
         )

   # --- end of _make_workers (...) ---
