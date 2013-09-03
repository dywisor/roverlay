# R overlay --
# -*- coding: utf-8 -*-
# Copyright (C) 2013 André Erdmann <dywi@mailerd.de>
# Distributed under the terms of the GNU General Public License;
# either version 2 of the License, or (at your option) any later version.

try:
   _LONG = long
except NameError:
   _LONG = int


class CounterException ( Exception ):
   pass
# --- end of CounterException ---

class CounterUnderflow ( CounterException ):
   pass
# --- end of CounterUnderflow ---


class IDGenerator ( object ):

   def __init__ ( self, first_value=0, use_long=False ):
      super ( IDGenerator, self ).__init__()
      self._initial_value = ( _LONG if use_long else int ) ( first_value - 1 )
      self._current_value = self._initial_value
   # --- end of __init__ (...) ---

   def reset ( self ):
      self._current_value = self._initial_value
   # --- end of reset (...) ---

   def inc ( self, step=1 ):
      self._current_value += step
      return self._current_value
   # --- end of inc (...) ---

   __next__ = inc

   def peek ( self ):
      val = self._current_value
      if val == self._initial_value:
         raise CounterException ( "no number generated so far!" )
      elif val < self._initial_value:
         raise CounterUnderflow()
      else:
         return val
   # --- end of peek (...) ---

   def __iter__ ( self ):
      return self
   # --- end of __iter__ (...) ---

# --- end of IDGenerator ---

class Counter ( IDGenerator ):

   def dec ( self, step=1 ):
      if self._current_value > self._initial_value:
         self._current_value -= step
         return self._current_value
      else:
         self._current_value = self._initial_value
         raise CounterUnderflow()
   # --- end of dec (...) ---

# --- end of Counter ---
