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

VMOD_INVERSE_MAP = {
   VMOD_EQ: VMOD_NE,
   VMOD_NE: VMOD_EQ,
   VMOD_LE: VMOD_GT,
   VMOD_LT: VMOD_GE,
   VMOD_GE: VMOD_LT,
   VMOD_GT: VMOD_LE,
}
VMOD_INVERSE_EQ_PRESERVE_MAP = {
   VMOD_EQ: VMOD_NE,
   VMOD_NE: VMOD_EQ,
   VMOD_LE: VMOD_GE,
   VMOD_LT: VMOD_GT,
   VMOD_GE: VMOD_LE,
   VMOD_GT: VMOD_LT,
}

def vmod_inverse ( vmod, keep_eq=True ):
   """Returns the inverse of vmod (== becomes !=, > becomes <=, ...).
   Returns VMOD_UNDEF if the operation is not supported.

   arguments:
   * vmod    -- int
   * keep_eq -- preserve VMOD_EQ
   """
   return (
      VMOD_INVERSE_EQ_PRESERVE_MAP if keep_eq else VMOD_INVERSE_MAP
   ).get ( vmod, VMOD_UNDEF )
# --- end of vmod_inverse (...) ---

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

   def __new__ ( cls, gen_tuple, *args, **kwargs ):
      return super ( VersionTuple, cls ).__new__ ( cls, gen_tuple )
   # --- end of __new__ (...) ---

   def get_comparator ( self, mode ):
      """Returns a function "this ~ other" that returns
      "<this version> <mode, e.g. VMOD_EQ> <other version>", e.g. <a> <= <b>.

      Returns None if mode is unknown / not supported.

      Note: Use vmod_inverse(mode) to get a comparator "other ~ this"

      arguments:
      * mode -- comparator 'mode' (VMOD_EQ, VMOD_NE, VMOD_LE, VMOD_GE,
                VMOD_LT, VMOD_GT)
      """
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

   def get_package_comparator ( self, mode, keep_eq=True ):
      """Returns a function "package ~ this" that returns
      "<package version> <inversed mode> <this version>"

      Returns None if mode is unknown / not supported.

      arguments:
      * mode    -- comparator 'mode' that will be inversed
                   (see get_comparator() and vmod_inverse())
      * keep_eq -- preserve VMOD_EQ when determining the inverse of mode
                   (Example: '<' becomes '>' if True, else '>=')
      """
      f = self.get_comparator ( vmod_inverse ( mode, keep_eq=keep_eq ) )
      return pkgver_decorator ( f ) if f is not None else None
   # --- end of get_package_comparator (...) ---

   def set_default_compare ( self, mode ):
      """Sets the default comparator.

      arguments:
      * mode -- comparator mode
      """
      self._default_compare = self.get_comparator ( mode )
   # --- end of set_default_compare (...) ---

   def compare ( self, other ):
      """Uses the default comparator to compare this object with another one
      and returns the result.

      arguments:
      * other --
      """
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
         #
         # ( k0, k1, ..., kN ) x ( l0, l1, ..., lN )
         #
         # from left to right (high to low)
         # if k_j < l_j
         #    return True (k <= j)
         # elif k_j == l_j
         #    continue with next
         # else
         #    return False (k > j)
         #
         # return True if last pair was equal
         for a, b in _zip_longest ( self, other, fillvalue=0 ):
            if a < b:
               return True
            elif a > b:
               return False
         else:
            return True
      else:
         return NotImplemented
   # --- end of __le__ (...) ---

   def __ge__ ( self, other ):
      if isinstance ( other, self.__class__ ):
         for a, b in _zip_longest ( self, other, fillvalue=0 ):
            if a > b:
               return True
            elif a < b:
               return False
         else:
            return True
      else:
         return NotImplemented
   # --- end of __ge__ (...) ---

   def __lt__ ( self, other ):
      if isinstance ( other, self.__class__ ):
         for a, b in _zip_longest ( self, other, fillvalue=0 ):
            if a < b:
               return True
            elif a > b:
               return False
         else:
            return False
      else:
         return NotImplemented
   # --- end of __lt__ (...) ---

   def __gt__ ( self, other ):
      if isinstance ( other, self.__class__ ):
         for a, b in _zip_longest ( self, other, fillvalue=0 ):
            if a > b:
               return True
            elif a < b:
               return False
         else:
            return False
      else:
         return NotImplemented
   # --- end of __gt__ (...) ---

   def __str__ ( self ):
      return '.'.join ( str(k) for k in self )
   # --- end of __str__ ( self )

# --- end of IntVersionTuple ---

class SuffixedIntVersionTuple ( VersionTuple ):
   # inherit VersionTuple: does not implement comparision functions

   def __init__ ( self, gen_tuple, suffix ):
      super ( SuffixedIntVersionTuple, self ).__init__ ( gen_tuple )
      self.suffix = suffix
   # --- end of __init__ (...) ---

   def get_suffix_str ( self ):
      ret = str ( self.suffix )
      if not ret or ret[0] == '_':
         return ret
      else:
         return '_' + ret
   # --- end of get_suffix_str (...) ---

   def __str__ ( self ):
      return '.'.join ( str(k) for k in self ) + self.get_suffix_str()
   # --- end of __str__ (...) ----
