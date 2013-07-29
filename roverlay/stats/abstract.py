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

class StatsVisualizer ( object ):

   def __init__ ( self, stats ):
      super ( StatsVisualizer, self ).__init__()
      self.stats = stats
      self.lines = None

      self.prepare()
   # --- end of __init__ (...) ---

   def prepare ( self ):
      raise MethodNotImplemented ( self, 'prepare' )
   # --- end of prepare (...) ---

   def __str__ ( self ):
      return '\n'.join ( self.lines )
   # --- end of __str__ (...) ---

# --- end of StatsVisualizer ---


class RoverlayStatsBase ( object ):

   @classmethod
   def get_new ( cls ):
      return cls()
   # --- end of get_new (...) ---

   def __init__ ( self, description=None ):
      super ( RoverlayStatsBase, self ).__init__()
      if description is not None:
         self.description = description
   # --- end of __init__ (...) ---

   def merge_with ( self, other ):
      my_cls    = self.__class__
      their_cls = other.__class__

      if (
         issubclass ( my_cls, their_cls )
         and hasattr ( their_cls, '_MEMBERS' )
      ):
         self.merge_members ( other, their_cls._MEMBERS )

      elif hasattr ( my_cls, '_MEMBERS' ):
         self.merge_members ( other, my_cls._MEMBERS )

      else:
         raise MethodNotImplemented ( self, 'merge_with' )
   # --- end of merge_with (...) ---

   def merge_members ( self, other, members ):
      for member in members:
         getattr ( self, member ).merge_with ( getattr ( other, member ) )
   # --- end of merge_members (...) ---

   def _iter_members ( self, nofail=False ):
      if not nofail or hasattr ( self, '_MEMBERS' ):
         for member in self.__class__._MEMBERS:
            yield getattr ( self, member )
   # --- end of _iter_members (...) ---

   def has_nonzero ( self ):
      if hasattr ( self, '_MEMBERS' ):
         for member in self._iter_members():
            if int ( member ) != 0:
               return member
      else:
         raise MethodNotImplemented ( self, 'has_nonzero' )
   # --- end of has_nonzero (...) ---

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
   pass
# --- end of RoverlayStats ---


class TimeStatsItem ( RoverlayStatsBase ):
   # doc TODO: note somewhere that those timestats are just approximate
   #           values

   def __init__ ( self, t_begin=None, t_end=None, description=None ):
      super ( TimeStatsItem, self ).__init__ ( description=description )
      self.time_begin = t_begin if t_begin is not None else time.time()
      self.time_end   = t_end
   # --- end of __init__ (...) ---

   def end ( self, t_end=None ):
      self.time_end = time.time() if t_end is None else t_end
   # --- end of end (...) ---

   def get_delta ( self ):
      if self.time_begin is None:
         return -1.0
      elif self.time_end is None:
         return -2.0
      else:
         return float ( self.time_end ) - float ( self.time_begin )
   # --- end of get_delta (...) ---

   def __str__ ( self ):
      return "{:.3f}s".format ( self.get_delta() )
   # --- end of __str__ (...) ---

# --- end of TimeStatsItem ---


class TimeStats ( RoverlayStats ):

   def __init__ ( self, description=None ):
      super ( TimeStats, self ).__init__ ( description=description )
      self._timestats = collections.OrderedDict()
   # --- end of __init__ (...) ---

   def merge_with ( self, other ):
      self._timestats.update ( other._timestats )
   # --- end of merge_with (...) ---

   def get ( self, key ):
      return self._timestats.get ( key, -1.0 )
   # --- end of get (...) ---

   def __getitem__ ( self, key ):
      return self._timestats [key]
   # --- end of __getitem__ (...) ---

   def begin ( self, key ):
      item = TimeStatsItem()
      self._timestats [key] = item
      return item
   # --- end of begin (...) ---

   def end ( self, key ):
      item = self._timestats [key]
      item.end()
      return item
   # --- end of end (...) ---

   def get_total ( self ):
      return float (
         sum ( filter (
            lambda k: k > 0.0,
            ( v.get_delta() for v in self._timestats.values() )
         ) )
      )
   # --- end of get_total (...) ---

   def get_total_str ( self,
      unknown_threshold=0.00001, ms_threshold=1.0, min_threshold=300.0,
      unknown_return=None
   ):
      t = self.get_total()
      if t < unknown_threshold:
         return unknown_return
      elif t < ms_threshold:
         return "{:.2f} ms".format ( t * 1000 )
      elif t > min_threshold:
         return "{:.2f} minutes".format ( t / 60.0 )
      else:
         return "{:.2f} seconds".format ( t )
   # --- end of get_total_str (...) ---

   def gen_str ( self ):
      desc = self.get_description_str()
      if desc:
         yield "{} ({:.3f}s)".format ( desc, self.get_total() )
      else:
         yield "total time: {:.3f}s".format ( self.get_total() )

      for key, value in self._timestats.items():
         yield "* {k}: {v}".format ( k=key, v=str ( value ) )
   # --- end of gen_str (...) ---

   def __str__ ( self ):
      return '\n'.join ( self.gen_str() )
   # --- end of __str__ (...) ---

# --- end of TimeStats ---


class Counter ( RoverlayStatsBase ):
   def __init__ ( self, description=None, initial_value=0 ):
      super ( Counter, self ).__init__ ( description=description )
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

   def __add__ ( self, other ):
      return self.total_count + int ( other )
   # --- end of __add__ (...) ---

   def __sub__ ( self, other ):
      return self.total_count - int ( other )
   # --- end of __sub__ (...) ---

   def has_details ( self ):
      return False
   # --- end of has_details (...) ---

   def reset ( self ):
      self.total_count = 0
      self.underflow   = False
   # --- end of reset (...) ---

   def get ( self ):
      return self.total_count
   # --- end of get (...) ---

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

   def has_details ( self ):
      return any ( int(v) != 0 for v in self._detailed_count.values() )
   # --- end of has_details (...) ---

   def iter_details ( self ):
      return ( kv for kv in self._detailed_count.items() if int(kv[1]) != 0 )
   # --- end of iter_details (...) ---

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
      self.dec_details_v ( details )
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

   @property
   def ratio ( self ):
      return self.get_ratio()
   # --- end of ratio (...) ---

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
