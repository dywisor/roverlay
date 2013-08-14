# R overlay -- stats collection, rrd database (using rrdtool)
# -*- coding: utf-8 -*-
# Copyright (C) 2013 André Erdmann <dywi@mailerd.de>
# Distributed under the terms of the GNU General Public License;
# either version 2 of the License, or (at your option) any later version.


# NOT using rrdtool's python bindings as they're available for python 2 only

import roverlay.db.rrdtool
from roverlay.db.rrdtool import RRDVariable, RRDArchive


class StatsDB ( roverlay.db.rrdtool.RRD ):

   def __init__ ( self, filepath, collector, step ):
      super ( StatsDB, self ).__init__ ( filepath )
      # COULDFIX:
      #  vars / RRA creation is only necessary when creating a new database
      #
      self.collector    = collector
      self.step         = int ( step )
      self.rrd_vars     = self.make_vars()
      self.rrd_archives = self.make_rra()
   # --- end of __init__ (...) ---

   def _do_create ( self, filepath ):
      return self._call_rrdtool (
         (
            'create', filepath,
            ##'--start', str ( self.INIT_TIME ),
            '--step', str ( self.step ),
         )
         + tuple ( v.get_key() for v in self.rrd_vars )
         + tuple ( v.get_key() for v in self.rrd_archives )
      )
   # --- end of _do_create (...) ---

   def update ( self ):
      self.add ( self.collector.get_all() )
   # --- end of update (...) ---

   def make_vars ( self ):
      heartbeat = 2 * self.step
      return tuple (
         RRDVariable ( k, 'DERIVE', val_min=0, heartbeat=heartbeat )
            for k in self.collector.NUMSTATS_KEYS
      )
   # --- end of make_vars (...) ---

   def make_rra ( self ):
      return (
         RRDArchive.new_day   ( 'LAST',    0.7, step=self.step ),
         RRDArchive.new_week  ( 'AVERAGE', 0.7, step=self.step ),
         RRDArchive.new_month ( 'AVERAGE', 0.7, step=self.step ),
      )
   # --- end of make_rra (...) ---

# --- end of StatsDB ---
