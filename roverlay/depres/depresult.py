# R overlay -- dependency resolution, depres result
# -*- coding: utf-8 -*-
# Copyright (C) 2013 André Erdmann <dywi@mailerd.de>
# Distributed under the terms of the GNU General Public License;
# either version 2 of the License, or (at your option) any later version.

from __future__ import print_function

__all__ = [ 'DepResult', 'DEP_NOT_RESOLVED', ]

import logging

import roverlay.depres.depenv

# two dep result classes are available
#  they're identical, but the "debugged-" one produces a lot of output
#  and calculates some operations twice
DEBUG = False

EMPTY_STR = ""

class _DepResult ( object ):
   """dependency resolution result data container"""

   def __init__ ( self,
      dep, score, matching_rule, dep_env=None, fuzzy=None
   ):
      """Initializes a dependency resolution result object.

      arguments:
      * dep           -- resolving dependency (string or None)
      * score         -- score (int)
      * matching_rule -- (reference to) the rule that resolved dep
      * dep_env       -- dependency environment (optional)
      * fuzzy         -- fuzzy dep (sub-)environment (optional)
      """
      super ( _DepResult, self ).__init__()
      self.dep        = dep
      self.score      = score
      #assert hasattr ( matching_rule, 'is_selfdep' )
      self.is_selfdep = matching_rule.is_selfdep if matching_rule else 0

      if self.is_selfdep:
         self.fuzzy = fuzzy
         self.resolving_package = matching_rule.resolving_package
   # --- end of DepResult ---

   def __eq__ ( self, other ):
      """Compares this dep result with another result or a string."""
      if isinstance ( other, str ):
         return str ( self ) == other
      elif isinstance ( other, DepResult ):
         return (
            self.score          == other.score
            and self.is_selfdep == other.is_selfdep
            and self.dep        == other.dep
         )
      else:
         return NotImplemented
   # --- end of __eq__ (...) ---

   def __hash__ ( self ):
      return id ( self )
   # --- end of __hash__ (...) ---

   def __bool__ ( self ):
      """Returns True if this dep result has a valid score (>0)."""
      return self.score > 0
      #and self.dep is not False
   # --- end of __bool__ (...) ---

   def __repr__ ( self ):
      return "<{} object {!r} at 0x{:x}>".format (
         self.__class__.__name__, self.dep, id ( self )
      )
   # --- end of __repr__ (...) ---

   def __str__ ( self ):
      return self.dep if self.dep is not None else EMPTY_STR
   # --- end of __str__ (...) ---

   def __getitem__ ( self, key ):
      # for backwards compatibility, indexing is supported
      print ( "FIXME: __getitem__ is deprecated" )
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
      """Prepares this dep result for selfdep validation by creating all
      necessary variables.
      """
      cat, sepa, pkg  = self.resolving_package.rpartition ( '/' )
      self.category   = cat
      self.package    = pkg
      self.candidates = list()
      self.link       = self.candidates.append

      if self.fuzzy:
         vmod    = self.fuzzy ['vmod']
         version = self.fuzzy ['version_tuple']

         # DEBUG bind
         self.version = version
         self.vmod    = vmod

         self.version_compare = version.get_package_comparator ( vmod )

      return self
   # --- end of prepare_selfdep_reduction (...) ---

   def deps_satisfiable ( self ):
      """Returns True if >this< selfdep is satisfiable, else False.
      This method should only be called _during_ selfdep validation.
      """
      # should be renamed to selfdeps_satisfiable
      return bool ( self.candidates )
   # --- end of deps_satisfiable (...) ---

   def is_valid ( self ):
      """Returns True if this dependency is valid, i.e. it either is not
      a selfdep or it is satisfiable.
      This method should be called _after_ selfdep validation.
      """
      return ( not self.is_selfdep ) or bool ( self.candidates )
   # --- end of is_valid (...) ---

   def link_if_version_matches ( self, p ):
      """Tries to a link a given package info as selfdep candidate.
      Returns True on success, else False.

      The link operation succeeds iff the package claims to be valid and
      its version is compatible.

      arguments:
      * p -- package info
      """
      if p.is_valid() and ( not self.fuzzy or self.version_compare ( p ) ):
         self.link ( p )
         return True
      else:
         return False
   # --- end of link_if_version_matches (...) ---

   def linkall_if_version_matches ( self, p_iterable ):
      """Tries to link several packages.
      Returns True if at least one package could be linked, else False.

      arguments:
      * p_iterable -- iterable that contains package info objects
      """
      any_added = False
      for p in p_iterable:
         if self.link_if_version_matches ( p ):
            any_added = True
      return any_added
   # --- end of linkall_if_version_matches (...) ---

   def do_reduce ( self ):
      """'reduce' operation for selfdep validation.

      Eliminates candidates that are no longer valid and returns the number
      of removed candidates (0 if nothing removed).
      """
      candidates = list (
         p for p in self.candidates if p.has_valid_selfdeps()
      )
      num_removed = len ( self.candidates ) - len ( candidates )
      if num_removed != 0:
         self.candidates = candidates
      return num_removed
   # --- end of do_reduce (...) ---

# --- end of _DepResult ---


class _DebuggedDepResult ( _DepResult ):
   LOGGER = logging.getLogger ( 'depresult' )

   def __init__ ( self, *args, **kwargs ):
      super ( _DebuggedDepResult, self ).__init__ ( *args, **kwargs )
      if self.is_selfdep:
         self.logger = self.__class__.LOGGER.getChild ( self.dep )

   def deps_satisfiable ( self ):
      self.logger.debug (
         "deps satisfiable? {}, <{}>".format (
            ( "Yes" if self.candidates else "No" ),
            ', '.join (
               (
                  "{}::{}-{}".format (
                     (
                        p['origin'].name if p.has ( 'origin' ) else "<undef>"
                     ),
                     p['name'], p['ebuild_verstr']
                  ) for p in self.candidates
               )
            )
         )
      )
      return super ( DebuggedDepResult, self ).deps_satisfiable()
   # --- end of deps_satisfiable (...) ---

   def link_if_version_matches ( self, p ):
      ret = super ( DebuggedDepResult, self ).link_if_version_matches ( p )

      pf = "{PN}-{PVR}".format (
         PN     = p ['name'],
         PVR    = p ['ebuild_verstr'],
      )

      info_append = ' p\'valid={valid!r}'.format (
         valid  = bool ( p.is_valid() ),
      )

      if self.fuzzy:
         info_append += (
            'this\'fuzzy={fuzzy!r}, vmatch={vmatch!r}, '
            'this\'version={myver!r}, p\'version={pver}, '
            'vcomp={vcomp!r} vmod={vmod:d}'.format (
               fuzzy  = bool ( self.fuzzy ),
               vmatch = self.version_compare ( p ),
               myver  = self.version,
               pver   = p ['version'],
               vcomp  = self.version_compare,
               vmod   = self.vmod,
            )
         )
      else:
         info_append += ', this\'fuzzy=False'


      if ret:
         self.logger.debug (
            "Added {PF} to candidate list.".format ( PF=pf )
            + info_append
         )
      else:
         # recalculate for logging
         self.logger.debug (
            'Rejected {PF} as candidate.'.format ( PF=pf )
            + info_append
         )

      return ret
   # --- end of link_if_version_matches (...) ---

   def do_reduce ( self ):
      """'reduce' operation for selfdep validation.

      Eliminates candidates that are no longer valid and returns the number
      of removed candidates (0 if nothing removed).
      """
      self.logger.debug ( "Checking candidates:" )
      for p in self.candidates:
         "{}-{}: {}".format (
            p['name'], p['ebuild_verstr'], p.has_valid_selfdeps()
         )
      ret = super ( DebuggedDepResult, self ).do_reduce()
      self.logger.debug ( "Dropped {:d} candidates.".format ( ret ) )
      return ret
   # --- end of do_reduce (...) ---

# --- end of _DebuggedDepResult ---

# DepResult <=  _DepResult | _DebuggedDepResult
DepResult = _DebuggedDepResult if DEBUG else _DepResult

# static object for unresolvable dependencies
DEP_NOT_RESOLVED = _DepResult ( dep=None, score=-2, matching_rule=None )
