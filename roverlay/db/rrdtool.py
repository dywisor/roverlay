# R overlay -- stats collection, wrapper for writing rrd databases
# -*- coding: utf-8 -*-
# Copyright (C) 2013 André Erdmann <dywi@mailerd.de>
# Distributed under the terms of the GNU General Public License;
# either version 2 of the License, or (at your option) any later version.

from __future__ import division

# NOT using rrdtool's python bindings as they're available for python 2 only

import logging
import os
import time

import roverlay.tools.runcmd
from roverlay.tools.runcmd import run_command

import roverlay.util

import roverlay.util.objects

class RRDVariable ( object ):

   DST = frozenset ({ 'GAUGE', 'COUNTER', 'DERIVE', 'ABSOLUTE', })

   def __init__ ( self,
      name, val_type, val_min=None, val_max=None, heartbeat=None, step=300
   ):
      if val_type not in self.DST:
         raise ValueError ( "invalid DS type: {!r}".format ( val_type ) )

      self.name      = name
      self.val_type  = val_type
      self.val_min   = val_min
      self.val_max   = val_max
      self.heartbeat = heartbeat or ( 2 * step )
   # --- end of __init__ (...) ---

   def get_key ( self ):
      mstr = lambda k: 'U' if k is None else str ( k )

      return "DS:{ds_name}:{DST}:{heartbeat}:{vmin}:{vmax}".format (
         ds_name=self.name, DST=self.val_type, heartbeat=self.heartbeat,
         vmin=mstr ( self.val_min ), vmax=mstr ( self.val_max )
      )
   # --- end of get_key (...) ---

   __str__ = get_key

# --- end of RRDVariable ---

class RRDArchive ( object ):

   CF_TYPES = frozenset ({ 'AVERAGE', 'MIN', 'MAX', 'LAST', })

   def __init__ ( self, cf, xff, steps, rows ):
      if cf not in self.CF_TYPES:
         raise ValueError ( "unknown CF: {!r}".format ( cf ) )
      elif not isinstance ( xff, float ):
         raise TypeError ( "xff must be a float." )
      elif xff < 0.0 or xff >= 1.0:
         raise ValueError (
            "xff not in range: 0.0 <= {:f} <= 1.0?".format ( xff )
         )
      elif not isinstance ( steps, int ) or steps <= 0:
         raise ValueError ( "steps must be an integer > 0." )

      elif not isinstance ( rows, int ) or rows <= 0:
         raise ValueError ( "rows must be an integer > 0." )

      self.cf    = cf
      self.xff   = float ( xff )
      self.steps = int ( steps )
      self.rows  = int ( rows )
   # --- end of __init__ (...) ---

   def get_key ( self ):
      return "RRA:{cf}:{xff}:{steps}:{rows}".format (
         cf=self.cf, xff=self.xff, steps=self.steps, rows=self.rows
      )
   # --- end of get_key (...) ---

   __str__ = get_key

   @classmethod
   def new_day ( cls, cf, xff, step=300 ):
      # one CDP per hour (24 rows)
      return cls ( cf, xff, 3600 // step, 24 )
   # --- end of new_day (...) ---

   @classmethod
   def new_week ( cls, cf, xff, step=300 ):
      # one CDP per 6h (28 rows)
      return cls ( cf, xff, 21600 // step, 42 )
   # --- end of new_week (...) ---

   @classmethod
   def new_month ( cls, cf, xff, step=300 ):
      # one CDP per day (31 rows)
      return cls ( cf, xff, (24*3600) // step, 31 )
   # --- end of new_month (...) ---

# --- end of RRDArchive ---

class RRD ( object ):
   # should be subclassed 'cause _do_create() is not implemented here

   RRDTOOL_CMDV_HEAD = ( 'rrdtool', )

   LOGGER = logging.getLogger ( 'RRD' )

   def __init__ ( self, filepath ):
      self.filepath       = filepath
      self._commit_buffer = []
      self._dbfile_exists = False
      self.logger         = self.__class__.LOGGER
      self.INIT_TIME      = self.time_now() - 10
   # --- end of __init__ (...) ---

   def time_now ( self ):
      return int ( time.time() )
   # --- end of time_now (...) ---

   def _call_rrdtool ( self, args, return_success=True ):
      return run_command (
         self.RRDTOOL_CMDV_HEAD + args, None, self.logger,
         return_success=return_success
      )
   # --- end of _call_rrdtool (...) ---

   @roverlay.util.objects.abstractmethod
   def _do_create ( self, filepath ):
      pass
   # --- end of _do_create (...) ---

   def create_if_missing ( self ):
      if self._dbfile_exists or not os.access ( self.filepath, os.F_OK ):
         return self.create()
   # --- end of create_if_missing (...) ---

   def create ( self ):
      roverlay.util.dodir_for_file ( self.filepath )
      self._do_create ( self.filepath )
      if os.access ( self.filepath, os.F_OK ):
         self._dbfile_exists = True
      else:
         raise Exception ( "database file does not exist." )
   # --- end of create (...) ---

   def add ( self, values, timestamp=None ):
      if timestamp is False:
         t = 'N'
      elif timestamp is None:
         t = str ( self.time_now() )
      else:
         t = str ( timestamp )

      self._commit_buffer.append (
         t + ':' + ':'.join ( str(v) for v in values )
      )
   # --- end of add (...) ---

   def clear ( self ):
      self._commit_buffer = []
   # --- end of clear (...) ---

   def commit ( self ):
      if self._commit_buffer:
         self.create_if_missing()
         self._call_rrdtool (
            ( 'update', self.filepath ) + tuple ( self._commit_buffer )
         )
         self.clear()
   # --- end of commit (...) ---

# --- end of RRD ---
