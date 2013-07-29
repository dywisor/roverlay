# R overlay -- stats collection, stats collector
# -*- coding: utf-8 -*-
# Copyright (C) 2013 André Erdmann <dywi@mailerd.de>
# Distributed under the terms of the GNU General Public License;
# either version 2 of the License, or (at your option) any later version.

import collections

from . import abstract
from . import base


class StatsCollector ( abstract.RoverlayStatsBase ):

   _instance = None

   _MEMBERS  = ( 'time', 'repo', 'distmap', 'overlay_creation', 'overlay', )

   @classmethod
   def get_instance ( cls ):
      return cls._instance
   # --- end of instance (...) ---

   def get_success_ratio ( self ):
      # success ratio for "this" run:
      #  new ebuilds / relevant package count (new packages - unsuitable,
      #   where unsuitable is e.g. "OS_Type not supported")
      #
      return abstract.SuccessRatio (
         num_ebuilds = self.overlay_creation.pkg_success,
         num_pkg     = self.overlay_creation.get_relevant_package_count(),
      )
   # --- end of get_success_ratio (...) ---

   def get_overall_success_ratio ( self ):
      # overall success ratio:
      #  "relevant ebuild count" / "guessed package count"
      #  ratio := <all ebuilds> / (<all ebuilds> + <failed packages>)
      #
      #
      #  *Not* accurate as it includes imported ebuilds
      #  (Still better than using the repo package count since that may
      #   not include old package files)
      #
      return abstract.SuccessRatio (
         num_ebuilds = self.overlay.ebuild_count,
         num_pkg     = (
            self.overlay.ebuild_count + self.overlay_creation.pkg_fail
         ),
      )
   # --- end of get_overall_success_ratio (...) ---

   def get_net_gain ( self ):
      return (
         self.overlay.ebuild_count - self.overlay.ebuilds_scanned
      )
   # --- end of get_net_gain (...) ---

   def __init__ ( self ):
      self.time             = abstract.TimeStats ( "misc time stats" )
      self.distmap          = base.DistmapStats()
      self.overlay          = base.OverlayStats()
      self.overlay_creation = base.OverlayCreationStats()
      self.repo             = base.RepoStats()
   # --- end of __init__ (...) ---

   def gen_str ( self ):
      yield "{success}, overall {osuccess}".format (
         success  = self.get_success_ratio(),
         osuccess = self.get_overall_success_ratio(),
      )
      yield ""

      for s in super ( StatsCollector, self ).gen_str():
         yield s
         yield ""
   # --- end of gen_str (...) ---

   def get_creation_str ( self ):
      return str ( CreationStatsVisualizer ( self ) )
   # --- end of to_creation_str (...) ---

# --- end of StatsCollector ---


class CreationStatsVisualizer ( abstract.StatsVisualizer ):

   def prepare ( self ):
      EMPTY_LINE = ""

      pkg_count    = self.stats.repo.pkg_count
      pkg_queued   = self.stats.overlay_creation.pkg_queued
      pkg_fail     = self.stats.overlay_creation.pkg_fail
      pkg_success  = self.stats.overlay_creation.pkg_success
      ebuild_delta = self.stats.get_net_gain()
      revbumps     = self.stats.overlay.revbump_count

      max_number_len = min (
         len ( str ( int ( k ) ) ) for k in (
            pkg_queued, pkg_fail, pkg_success
         )
      )
      max_number_len = min ( 5, max_number_len )

      success_ratio         = self.stats.get_success_ratio()
      overall_success_ratio = self.stats.get_overall_success_ratio()


      timestats = (
         ( 'scan_overlay', self.stats.overlay.scan_time.get_total_str() ),
         ( 'add_packages', self.stats.repo.queue_time.get_total_str() ),
         (
            'ebuild_creation',
            self.stats.overlay_creation.creation_time.get_total_str()
         ),
         ( 'write_overlay',  self.stats.overlay.write_time.get_total_str() ),
      )

      try:
         max_time_len = max ( len(k) for k, v in timestats if v is not None )
      except ValueError:
         # empty sequence -> no timestats
         max_time_len = -1
      else:
         # necessary?
         max_time_len = min ( 39, max_time_len )


      # create lines
      lines   = collections.deque()
      unshift = lines.appendleft
      append  = lines.append

      numstats = lambda k, s: "{num:<{l}d} {s}".format (
         num=int ( k ), s=s, l=max_number_len
      )


      append (
         'success ratio {s_i:.2%} (overall {s_o:.2%})'.format (
            s_i = success_ratio.get_ratio(),
            s_o = overall_success_ratio.get_ratio()
         )
      )
      append ( EMPTY_LINE )

      append (
         "{e:+d} ebuilds ({r:d} revbumps)".format (
            e=ebuild_delta, r=int ( revbumps )
         )
      )
      append ( EMPTY_LINE )

      if int ( pkg_count ) != int ( pkg_queued ):
         append ( numstats (
            pkg_queued,
            '/ {n:d} packages added to the ebuild creation queue'.format (
               n=int ( pkg_count )
            )
         ) )
      else:
         append ( numstats (
            pkg_queued, 'packages added to the ebuild creation queue'
         ) )

      append ( numstats (
         pkg_success, 'packages passed ebuild creation'
      ) )

      append ( numstats (
         pkg_fail, 'packages failed ebuild creation'
      ) )

      if pkg_fail.has_details() and int ( pkg_fail ) != 0:
         append ( EMPTY_LINE )
         append ( "Details for ebuild creation failure:" )
         details = sorted (
            ( ( k, int(v) ) for k, v in pkg_fail.iter_details() ),
            key=lambda kv: kv[1]
         )
         dlen = len ( str ( max ( details, key=lambda kv: kv[1] ) [1] ) )

         for key, value in details:
            append ( "* {v:>{l}d}: {k}".format ( k=key, v=value, l=dlen ) )
      # -- end if <have pkg_fail details>

      if max_time_len > 0:
         # or >= 0
         append ( EMPTY_LINE )
         for k, v in timestats:
            if v is not None:
               append (
                  "time for {0:<{l}} : {1}".format ( k, v, l=max_time_len )
               )
      # -- end if timestats


      append ( EMPTY_LINE )

      # add header/footer line(s)
      max_line_len = 2 + min ( 78, max ( len(s) for s in lines ) )
      unshift (
         "{0:-^{1}}\n".format ( " Overlay creation stats ", max_line_len )
      )
      append ( max_line_len * '-' )

      self.lines = lines
   # --- end of gen_str (...) ---
# --- end of CreationStatsVisualizer ---

static = StatsCollector()
StatsCollector._instance = static
