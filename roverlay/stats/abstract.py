# R overlay -- stats collection, data types
# -*- coding: utf-8 -*-
# Copyright (C) 2013 André Erdmann <dywi@mailerd.de>
# Distributed under the terms of the GNU General Public License;
# either version 2 of the License, or (at your option) any later version.

from __future__ import division

import collections
import time

class MethodNotImplemented ( NotImplementedError ):
   def __init__ ( self, obj, method ):
      super ( MethodNotImplemented, self ).__init__ (
         "{n}.{f}()".format ( n=obj.__class__.__name__, f=method )
      )
   # --- end of __init__ (...) ---

# --- end of MethodNotImplemented ---


class RoverlayStatsBase ( object ):

   @classmethod
   def get_new ( cls ):
      return cls()
   # --- end of get_new (...) ---

   def merge_with ( self, other ):
      if hasattr ( self, '_MEMBERS' ):
         self.merge_members ( other )
      else:
         raise MethodNotImplemented ( self, 'merge_with' )
   # --- end of merge_with (...) ---

   def merge_members ( self, other ):
      for member in self.__class__._MEMBERS:
         getattr ( self, member ).merge_with ( getattr ( other, member ) )
   # --- end of merge_members (...) ---

   def _iter_members ( self, nofail=False ):
      if not nofail or hasattr ( self, '_MEMBERS' ):
         for member in self.__class__._MEMBERS:
            yield getattr ( self, member )
   # --- end of _iter_members (...) ---

   def reset_members ( self ):
      for member in self._iter_members():
         member.reset()
   # --- end of reset_members (...) ---

   def reset ( self ):
      if hasattr ( self.__class__, '_MEMBERS' ):
         self.reset_members()
      else:
         raise MethodNotImplemented ( self, 'reset' )
   # --- end of reset (...) ---

   def get_description_str ( self ):
      return (
         getattr ( self, 'description', None ) or
         getattr ( self, 'DESCRIPTION', None )
      )
   # --- end of get_description_str (...) ---

   def gen_str ( self ):
      desc = self.get_description_str()
      if desc:
         yield desc

      for member in self._iter_members( nofail=True ):
         yield str ( member )
   # --- end of gen_str (...) ---

   def __str__ ( self ):
      ret = '\n'.join ( self.gen_str() )
      if ret:
         return ret
      else:
         raise MethodNotImplemented ( self, '__str__' )
   # --- end of __str__ (...) ---

# --- end of RoverlayStatsBase ---


class RoverlayStats ( RoverlayStatsBase ):

   def get_time ( self ):
      return time.time()
   # --- end of get_time (...) ---

   def get_time_delta ( self, start, stop=None ):
      t_stop = self.get_time() if stop is None else stop
      return ( start - t_stop, t_stop )
   # --- end of get_time_delta (...) ---

# --- end of RoverlayStats ---

class Counter ( RoverlayStatsBase ):
   def __init__ ( self, description=None, initial_value=0 ):
      super ( Counter, self ).__init__()
      self.description = description
      self.total_count = initial_value
      self.underflow   = False
   # --- end of __init__ (...) ---

   def __int__ ( self ):
      return self.total_count
   # --- end of __int__ (...) ---

   def __float__ ( self ):
      return float ( self.total_count )
   # --- end of __float__ (...) ---

   def reset ( self ):
      self.total_count = 0
      self.underflow   = False
   # --- end of reset (...) ---

   def inc ( self, step=1 ):
      self.total_count += step
   # --- end of inc (...) ---

   def dec ( self, step=1 ):
      self.total_count -= step
      if self.total_count < 0:
         self.underflow = True
   # --- end of dec (...) ---

   def merge_with ( self, other ):
      self.total_count += other.total_count
      if other.underflow:
         self.underflow = True
   # --- end of merge_with (...) ---

   def gen_str ( self ):
      desc = self.get_description_str()
      if desc:
         yield "{}: {:d}".format ( desc, self.total_count )
      else:
         yield str ( self.total_count )

      if self.underflow:
         yield "*** underflow detected ***"
   # --- end of gen_str (...) ---

# --- end of Counter ---


class DetailedCounter ( Counter ):
   def __init__ ( self, description=None ):
      super ( DetailedCounter, self ).__init__ ( description=description )
      self._detailed_count = collections.defaultdict ( int )
   # --- end of __init__ (...) ---

   def __getitem__ ( self, key ):
      if key in self._detailed_count:
         return self._detailed_count [key]
      else:
         raise KeyError ( key )
   # --- end of __getitem__ (...) ---

   def get ( self, key=None, fallback=0 ):
      if key is None:
         return self.total_count
      elif key in self._detailed_count:
         return self._detailed_count [key]
      else:
         return fallback
   # --- end of get (...) ---

   def reset ( self ):
      super ( DetailedCounter, self ).reset()
      self._detailed_count.clear()
   # --- end of reset (...) ---

   def inc_details_v ( self, details ):
      for k in details:
         self._detailed_count [k] += 1
   # --- end of inc_details_v (...) ---

   def inc ( self, *details, **kw ):
      super ( DetailedCounter, self ).inc ( **kw )
      self.inc_details_v ( details )
   # --- end of inc (...) ---

   def inc_details ( self, *details ):
      self.inc_details_v ( details )
   # --- end of inc_details (...) ---

   def dec_details_v ( self, details ):
      # do not check / fail if self._detailed_count [k] > 0
      #  simply keep the negative value
      for k in details:
         self._detailed_count [k] -= 1
         if self._detailed_count [k] < 0:
            self.underflow = True
   # --- end of dec_details_v (...) ---

   def dec ( self, *details, **kw ):
      super ( DetailedCounter, self ).dec ( **kw )
      self.dec_details_v ( details )
   # --- end of dec (...) ---

   def dec_details ( self, *details ):
      self.dec_details_v ( Details )
   # --- end of dec_details (...) ---

   def merge_with ( self, other ):
      super ( DetailedCounter, self ).merge_with ( other )
      for key, value in other._detailed_count.items():
         self._detailed_count [key] += value
   # --- end of merge_with (...) ---

   def gen_str ( self ):
      desc = self.get_description_str()
      if desc:
         yield desc

      yield "total: {:d}".format ( self.total_count )
      for key, value in self._detailed_count.items():
         yield "* {k}: {v:d}".format ( k=key, v=value )

      if self.underflow:
         yield "*** underflow detected ***"
   # --- end of gen_str (...) ---

# --- end of DetailedCounter ---


class SuccessRatio ( object ):

   def __init__ ( self, num_ebuilds, num_pkg ):
      super ( SuccessRatio, self ).__init__()
      self.ebuild_count = int ( num_ebuilds )
      self.pkg_count    = int ( num_pkg )
   # --- end of __init__ (...) ---

   def get_ratio ( self ):
      if self.pkg_count == self.ebuild_count:
         # 0/0, ..., K/K: "success" := 1.0
         return 1.0
      elif self.pkg_count < 1:
         # K/0: bad ratio, use fixed value
         return -1.0
      else:
         return float ( self.ebuild_count ) / float ( self.pkg_count )
   # --- end of get_ratio (...) ---

   def __float__ ( self ):
      return self.get_ratio()
   # --- end of __float__ (...) ---

   def __int__ ( self ):
      return int ( self.get_ratio() )
   # --- end of __int__ (...) ---

   def __str__ ( self ):
      return "{:.3%}".format ( self.get_ratio() )
   # --- end of __str__ (...) ---

# --- end of SuccessRatio ---
