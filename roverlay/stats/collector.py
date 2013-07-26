# R overlay -- stats collection, stats collector
# -*- coding: utf-8 -*-
# Copyright (C) 2013 André Erdmann <dywi@mailerd.de>
# Distributed under the terms of the GNU General Public License;
# either version 2 of the License, or (at your option) any later version.

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


# --- end of StatsCollector ---

static = StatsCollector()
StatsCollector._instance = static
