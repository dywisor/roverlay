# R overlay --
# -*- coding: utf-8 -*-
# Copyright (C) 2013 André Erdmann <dywi@mailerd.de>
# Distributed under the terms of the GNU General Public License;
# either version 2 of the License, or (at your option) any later version.

import roverlay.util.objects

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


class AbstractCounter ( object ):

   def __init__ ( self, first_value=0, use_long=False ):
      super ( AbstractCounter, self ).__init__()
      self._initial_value = ( _LONG if use_long else int ) ( first_value - 1 )
      self._current_value = self._initial_value
   # --- end of __init__ (...) ---

   @roverlay.util.objects.abstractmethod
   def set_value ( self, value ):
      pass
   # --- end of set_value (...) ---

   @roverlay.util.objects.abstractmethod
   def reset ( self ):
      pass
   # --- end of reset (...) ---

   def change_value ( self, delta ):
      return self.set_value ( self._current_value + delta )
   # --- end of change_value (...) ---

   def get_value ( self, value ):
      return self._current_value
   # --- end of get_value (...) ---

   def get_value_unsafe ( self, value ):
      return self._current_value
   # --- end of get_value_unsafe (...) ---

   def inc ( self, step=1 ):
      return self.change_value ( step )
   # --- end of inc (...) ---

   def dec ( self, step=1 ):
      return self.change_value ( (-1) * step )
   # --- end of dec (...) ---

   def __next__ ( self ):
      return self.inc()
   # --- end of __next__ (...) ---

   def __iter__ ( self ):
      return self
   # --- end of __iter__ (...) ---

# --- end of AbstractCounter ---


class UnsafeCounter ( AbstractCounter ):

   def reset ( self ):
      self.current_value = self._initial_value
   # --- end of reset (...) ---

   def set_value ( self, value ):
      if value <= self._initial_value:
         raise CounterUnderflow ( value )
      else:
         self._current_value = value
         return value
   # --- end of set_value (...) ---

# --- end of UnsafeCounter ---


class IDGenerator ( UnsafeCounter ):
   pass
# --- end of IDGenerator ---
