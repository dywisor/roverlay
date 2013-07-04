# R overlay -- dependency resolution, depres result
# -*- coding: utf-8 -*-
# Copyright (C) 2013 André Erdmann <dywi@mailerd.de>
# Distributed under the terms of the GNU General Public License;
# either version 2 of the License, or (at your option) any later version.

__all__ = [ 'DepResult', 'DEP_NOT_RESOLVED', ]

import roverlay.depres.depenv

EMPTY_STR = ""

class DepResult ( object ):

   # TODO/FIXME: define those constants somewhere else
   #  (especially VMOD_??)
   #
   VMOD_COMPARE_MAP = {
      # p.version_compare_* functions are TODO
      roverlay.depres.depenv.DepEnv.VMOD_EQ: (
         lambda p: p.version_compare_eq
      ),
      roverlay.depres.depenv.DepEnv.VMOD_NE: (
         lambda p: p.version_compare_ne
      ),
      roverlay.depres.depenv.DepEnv.VMOD_GT: (
         lambda p: p.version_compare_gt
      ),
      roverlay.depres.depenv.DepEnv.VMOD_GE: (
         lambda p: p.version_compare_ge
      ),
      roverlay.depres.depenv.DepEnv.VMOD_LT: (
         lambda p: p.version_compare_lt
      ),
      roverlay.depres.depenv.DepEnv.VMOD_LE: (
         lambda p: p.version_compare_le
      ),
   }

   def __init__ ( self,
      dep, score, matching_rule, dep_env=None, fuzzy=None
   ):
      self.dep        = dep
      self.score      = score
      #assert hasattr ( matching_rule, 'is_selfdep' )
      self.is_selfdep = matching_rule.is_selfdep if matching_rule else 0

      if self.is_selfdep:
         self.fuzzy = fuzzy
         self.resolving_package = matching_rule.resolving_package
   # --- end of DepResult ---

   def __eq__ ( self, other ):
      if isinstance ( other, str ):
         return str ( self ) == other
      elif isinstance ( other, DepResult ):
         return (
            self.score == other.score
            and self.is_selfdep == other.is_selfdep
            and self.dep == other.dep
         )
      else:
         return NotImplemented
   # --- end of __eq__ (...) ---

   def __hash__ ( self ):
      #return hash ( self.__dict__.values() )
      return hash (( self.dep, self.score, self.is_selfdep ))
   # --- end of __hash__ (...) ---

   def __bool__ ( self ):
      return self.score > 0
      #and self.dep is not False
   # --- end of __bool__ (...) ---

   def __str__ ( self ):
      return self.dep if self.dep is not None else EMPTY_STR
   # --- end of __str__ (...) ---

   def __getitem__ ( self, key ):
      # for backwards compatibility, indexing is supported
      if key == 0:
         return self.score
      elif key == 1:
         return self.dep
      elif isinstance ( key, int ):
         raise IndexError ( key )
      else:
         raise KeyError ( key )
   # --- end of __getitem__ (...) ---

   def prepare_selfdep_reduction ( self ):
      cat, sepa, pkg  = self.resolving_package.rpartition ( '/' )
      self.category   = cat
      self.package    = pkg
      self.candidates = list()
      self.link       = self.candidates.append

      if self.fuzzy:
         vmod         = self.fuzzy ['vmod']
         self.version = self.fuzzy ['version_tuple']
         self._version_compare = self.VMOD_COMPARE_MAP [vmod]
         self.version_compare  = (
            lambda p: self._version_compare ( p ) ( self.version )
         )
   # --- end of prepare_selfdep_reduction (...) ---

   def deps_satisfiable ( self ):
      return bool ( self.candidates )

   def link_if_version_matches ( self, p ):
      if not self.fuzzy or self.version_compare ( p ):
         self.link ( p )
         return True
      else:
         return False
   # --- end of link_if_version_matches (...) ---

   def reduce ( self ):
      candidates = list (
         p for p in self.candidates if p.has_valid_selfdeps()
      )
      num_removed = len ( self.candidates ) - len ( candidates )
      if num_removed != 0:
         self.candidates = candidates
      return num_removed
   # --- end of reduce (...) ---

# --- end of DepResult ---

DEP_NOT_RESOLVED = DepResult ( dep=None, score=-2, matching_rule=None )
