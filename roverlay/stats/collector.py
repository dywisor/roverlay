# R overlay -- stats collection, stats collector
# -*- coding: utf-8 -*-
# Copyright (C) 2013 André Erdmann <dywi@mailerd.de>
# Distributed under the terms of the GNU General Public License;
# either version 2 of the License, or (at your option) any later version.

import time

import roverlay.config.static

from . import abstract
from . import base
from . import dbcollector
from . import visualize
from . import filedb



class StatsCollector ( abstract.RoverlayStatsBase ):

   _instance = None

   _MEMBERS  = ( 'time', 'repo', 'distmap', 'overlay_creation', 'overlay', )

   @classmethod
   def get_instance ( cls ):
      return cls._instance
   # --- end of instance (...) ---

   def overlay_has_any_changes ( self ):
      """Returns True if the resulting overlay has any changes (according to
      stats).
      """
      return any ( x.has_changes() for x in self.iter_members() )
   # --- end of overlay_has_any_changes (...) ---

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
      super ( StatsCollector, self ).__init__()

      self.time             = abstract.TimeStats ( "misc time stats" )
      self.distmap          = base.DistmapStats()
      self.overlay          = base.OverlayStats()
      self.overlay_creation = base.OverlayCreationStats()
      self.repo             = base.RepoStats()
      self.db_collector     = None
      self._database        = None
   # --- end of __init__ (...) ---

   def setup_database ( self, config=None ):
      conf = (
         config if config is not None else roverlay.config.static.access()
      )

      self.db_collector = dbcollector.StatsDBCollector ( self )
      self._database    = filedb.StatsDBFile (
         filepath  = conf.get_or_fail ( 'STATS.dbfile' ),
         collector = self.db_collector,
      )
   # --- end of setup_database (...) ---

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
      return str ( visualize.CreationStatsVisualizer ( self ) )
   # --- end of to_creation_str (...) ---

   def write_database ( self ):
      self.db_collector.update()
      self._database.update()
      self._database.commit()
   # --- end of write_database (...) ---

# --- end of StatsCollector ---


static = StatsCollector()
StatsCollector._instance = static
