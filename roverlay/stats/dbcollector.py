# R overlay -- stats collection, prepare data for db storage
# -*- coding: utf-8 -*-
# Copyright (C) 2013 André Erdmann <dywi@mailerd.de>
# Distributed under the terms of the GNU General Public License;
# either version 2 of the License, or (at your option) any later version.

import collections
import weakref

class StatsDBCollector ( object ):
   VERSION = 0

   # 'pc' := package count(er), 'ec' := ebuild _
   NUMSTATS_KEYS = (
      'pc_repo', 'pc_distmap', 'pc_filtered', 'pc_queued', 'pc_success',
      'pc_fail', 'pc_fail_empty', 'pc_fail_dep', 'pc_fail_selfdep',
      'pc_fail_err',
      'ec_pre', 'ec_post', 'ec_written', 'ec_revbump',
   )
   NUMSTATS = collections.namedtuple (
      "numstats", ' '.join ( NUMSTATS_KEYS )
   )

   TIMESTATS_KEYS = ()
   TIMESTATS = collections.namedtuple (
      "timestats", ' '.join ( TIMESTATS_KEYS )
   )

   def __init__ ( self, stats ):
      super ( StatsDBCollector, self ).__init__()
      self.stats            = weakref.ref ( stats )
      self._collected_stats = None
   # --- end of __init__ (...) ---

   def update ( self ):
      self._collected_stats = self.make_all()
   # --- end of update (...) ---

   def make_numstats ( self ):
      stats     = self.stats()
      ov_create = stats.overlay_creation
      ov        = stats.overlay

      return self.__class__.NUMSTATS (
         pc_repo         = int ( stats.repo.pkg_count ),
         pc_distmap      = int ( stats.distmap.pkg_count ),
         pc_filtered     = int ( ov_create.pkg_filtered ),
         pc_queued       = int ( ov_create.pkg_queued ),
         pc_success      = int ( ov_create.pkg_success ),
         pc_fail         = int ( ov_create.pkg_fail ),
         pc_fail_empty   = ov_create.pkg_fail.get ( 'empty_desc' ),
         pc_fail_dep     = ov_create.pkg_fail.get ( 'unresolved_deps' ),
         pc_fail_selfdep = ov_create.pkg_fail.get ( 'bad_selfdeps' ),
         pc_fail_err     = ov_create.pkg_fail.get ( 'exception' ),
         ec_pre          = int ( ov.ebuilds_scanned ),
         ec_post         = int ( ov.ebuild_count ),
         ec_written      = int ( ov.ebuilds_written ),
         ec_revbump      = int ( ov.revbump_count ),
      )
   # --- end of make_numstats (...) ---

   def make_timestats ( self ):
      return ()
   # --- end of make_timestats (...) ---

   def make_all ( self ):
      return self.make_numstats() + self.make_timestats()
   # --- end of make_all (...) ---

   def get_all ( self ):
      return self._collected_stats
   # --- end of get_all (...) ---

# --- end of StatsDBCollector #v0 ---
