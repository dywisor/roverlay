# R overlay --
# -*- coding: utf-8 -*-
# Copyright (C) 2013 André Erdmann <dywi@mailerd.de>
# Distributed under the terms of the GNU General Public License;
# either version 2 of the License, or (at your option) any later version.

import sys
import itertools

if sys.hexversion >= 0x3000000:
   _zip_longest = itertools.zip_longest
else:
   _zip_longest = itertools.izip_longest


# integer representation of version comparision
VMOD_NONE  = 0
VMOD_UNDEF = 1
VMOD_NOT   = 2
VMOD_EQ    = 4
VMOD_NE    = VMOD_NOT | VMOD_EQ
VMOD_GT    = 8
VMOD_GE    = VMOD_EQ | VMOD_GT
VMOD_LT    = 16
VMOD_LE    = VMOD_EQ | VMOD_LT


def pkgver_decorator ( func ):
   def wrapped ( p, *args, **kwargs ):
      return func ( p._info ['version'], *args, **kwargs )
   # --- end of wrapped (...) ---
   wrapped.__name__ = func.__name__
   wrapped.__doc__  = func.__doc__
   wrapped.__dict__.update ( func.__dict__ )
   return wrapped
# --- end of pkgver_decorator (...) ---


class VersionTuple ( tuple ):

   def __init__ ( self, *args, **kwargs ):
      super ( VersionTuple, self ).__init__ ( *args, **kwargs )
   # --- end of __init__ (...) ---

   def get_comparator ( self, mode ):
      if not mode or mode & VMOD_UNDEF:
         return None
      elif mode & VMOD_EQ:
         if mode == VMOD_EQ:
            return self.__eq__
         elif mode == VMOD_NE:
            return self.__ne__
         elif mode == VMOD_LE:
            return self.__le__
         elif mode == VMOD_GE:
            return self.__ge__
      elif mode == VMOD_LT:
         return self.__lt__
      elif mode == VMOD_GT:
         return self.__gt__

      return None
   # --- end of get_comparator (...) ---

   def get_package_comparator ( self, mode ):
      f = self.get_comparator ( mode )
      return pkgver_decorator ( f ) if f is not None else None
   # --- end of get_package_comparator (...) ---

   def set_default_compare ( self, mode ):
      self._default_compare = self.get_comparator ( mode )
   # --- end of set_default_compare (...) ---

   def compare ( self, other ):
      self._default_compare ( other )
   # --- end of compare (...) ---

# --- end of VersionTuple ---


class IntVersionTuple ( VersionTuple ):

   def iter_compare ( self, other ):
      return _zip_longest ( self, other, fillvalue=0 )
   # --- end of _iter_compare (...) ---

   def __eq__ ( self, other ):
      if isinstance ( other, self.__class__ ):
         return all ( a == b
            for a, b in _zip_longest ( self, other, fillvalue=0 )
         )
      else:
         return NotImplemented
   # --- end of __eq__ (...) ---

   def __ne__ ( self, other ):
      if isinstance ( other, self.__class__ ):
         return any ( a != b
            for a, b in _zip_longest ( self, other, fillvalue=0 )
         )
      else:
         return NotImplemented
   # --- end of __ne__ (...) ---

   def __le__ ( self, other ):
      if isinstance ( other, self.__class__ ):
         return all ( a <= b
            for a, b in _zip_longest ( self, other, fillvalue=0 )
         )
      else:
         return NotImplemented
   # --- end of __le__ (...) ---

   def __ge__ ( self, other ):
      if isinstance ( other, self.__class__ ):
         return all ( a >= b
            for a, b in _zip_longest ( self, other, fillvalue=0 )
         )
      else:
         return NotImplemented
   # --- end of __ge__ (...) ---

   def __lt__ ( self, other ):
      if isinstance ( other, self.__class__ ):
         return all ( a < b
            for a, b in _zip_longest ( self, other, fillvalue=0 )
         )
      else:
         return NotImplemented
   # --- end of __lt__ (...) ---

   def __gt__ ( self, other ):
      if isinstance ( other, self.__class__ ):
         return all ( a > b
            for a, b in _zip_longest ( self, other, fillvalue=0 )
         )
      else:
         return NotImplemented
   # --- end of __gt__ (...) ---

# --- end of IntVersionTuple ---
