# R overlay -- ebuild creation, ebuild construction
# -*- coding: utf-8 -*-
# Copyright (C) 2012 André Erdmann <dywi@mailerd.de>
# Distributed under the terms of the GNU General Public License;
# either version 2 of the License, or (at your option) any later version.

"""ebuild construction

This module provides one class, Ebuilder, that accepts evars and produces
an ebuild (as string).
"""

__all__ = [ 'Ebuilder', ]

class Ebuilder ( object ):
   """Used to create ebuilds."""

   def __init__ ( self ):
      self._evars = dict()
      # newlines \n will be inserted after an evar if the priority
      # delta (current evar, next evar) is >= this value.
      # <= 0 means newline after each statement
      self.min_newline_distance = 20


   def get_lines ( self ):
      """Creates and returns (ordered) text lines."""
      EMPTY_STR = ""
      evar_list = sorted (
         self._evars.values(), key=lambda e: ( e.priority, e.name )
      )
      last      = len ( evar_list ) - 1
      want_newline = False

      for index, e in enumerate ( evar_list ):
         if e.active():
            varstr = str ( e )
            if varstr:
               if want_newline:
                  yield EMPTY_STR
                  want_newline = False

               yield varstr
               if index < last and self.min_newline_distance < abs (
                  evar_list [index + 1].priority - e.priority
               ):
                  want_newline = True
      # -- end for;
   # --- end of get_lines (...) ---


   def to_str ( self ): return '\n'.join ( self.get_lines() )
   __str__ = to_str

   def use ( self, *evar_list ):
      """Adds evars to this Ebuilder.

      arguments:
      * *evar_list --
      """
      self.use_list ( evar_list )
   # --- end of use (...) ---

   def use_list ( self, evar_list ):
      for e in evar_list:
         if e is not None:
            assert e.name not in self._evars
            self._evars [e.name] = e
   # --- end of use_list (...) ---

   def has ( self, evar_name ):
      """Returns True if an evar with name evar_name exists.

      arguments:
      * evar_name --
      """
      return evar_name in self._evars
   # --- end of has (...) ---

   __contains__ = has

   def get ( self, evar_name ):
      return self._evars.get ( evar_name, None )
   # --- end of get (...) ---

   def get_names ( self ):
      """Yields all evar names."""
      return self._evars.keys()
   # --- end of get_names (...) ---
