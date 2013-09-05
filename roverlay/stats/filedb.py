# R overlay -- stats collection, flat/plain file database
# -*- coding: utf-8 -*-
# Copyright (C) 2013 André Erdmann <dywi@mailerd.de>
# Distributed under the terms of the GNU General Public License;
# either version 2 of the License, or (at your option) any later version.

import time

from . import rating


import roverlay.util.fileio
import roverlay.strutil

from roverlay.strutil import unquote



class StatsDBFile ( roverlay.util.fileio.TextFile ):

   DEFAULT_FILE_VERSION = 0

   @classmethod
   def new_stats_reader ( cls, filepath ):
      instance = cls ( filepath=filepath, collector=None )
      if instance.try_read():
         instance.make_cache()
      return instance
   # --- end of new_stats_reader (...) ---

   def __init__ ( self, filepath, collector, compression=None ):
      super ( StatsDBFile, self ).__init__ (
         filepath=filepath, compression=compression
      )
      self.collector    = collector
      self.file_version = None

      self._data        = dict()
      self.cache        = None
   # --- end of __init__ (...) ---

   def start_reading ( self ):
      self._data.clear()
      self.file_version = self.__class__.DEFAULT_FILE_VERSION
   # --- end of start_reading (...) ---

   def update ( self ):
      self._data.clear()
      self._data.update ( self.collector.get_numstats  ( as_dict=True ) )
      self._data.update ( self.collector.get_timestats ( as_dict=True ) )
      self._data ['t_update'] = time.time()
      self.set_dirty()
   # --- end of update (...) ---

   def commit ( self ):
      return self.write()
   # --- end of commit (...) ---

   def gen_lines ( self ):
      yield ">{:d}<".format ( self.__class__.DEFAULT_FILE_VERSION )
      if self._data:
         for key, value in sorted ( self._data.items(), key=lambda kv: kv[0] ):
            yield "{k!s}=\'{v!s}\'".format ( k=key, v=value )
   # --- end of gen_lines (...) ---

   def parse_line ( self, line ):
      if line:
         key, eq_sign, value_quoted = line.partition ( '=' )
         if eq_sign:
            value = unquote ( value_quoted )

            if key[1:3] == 'c_':
               # is a counter (int)
               self._data [key] = int ( value )
            elif key[0:2] == 't_':
               # is a time (float)
               self._data [key] = float ( value )
            else:
               self._data [key] = value
         else:
            raise ValueError ( line )
      return True
   # --- end of parse_line (...) ---

   def parse_header_line ( self, line ):
      if len ( line ) > 2 and line[0] == '>' and line[-1]  == '<':
         self.file_version = int ( line[1:-1] )
         return True
      else:
         return self.parse_line ( line )
   # --- end of parse_header_line (...) ---

   def make_cache ( self ):
      # creates self.cache, which contains the same data as self._data, but
      # in a format known/accepted by the status script
      #
      if self._data:
         NUMSTATS_KEYS = frozenset ( rating.NUMSTATS.keys() )
         t_update = self._data.get ( 't_update', None )
         if t_update is not None:
            t_update = round ( t_update, 0 )

         self.cache = {
            'values' : {
               k: v for k, v in self._data.items() if k in NUMSTATS_KEYS
            },
            'lastupdate': t_update,
         }
         return True
      else:
         self.cache = dict()
         return False
   # --- end of make_cache (...) ---

# --- end of StatsDBFile ---
