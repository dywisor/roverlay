# R overlay -- dependency resolution, dependency environment
# -*- coding: utf-8 -*-
# Copyright (C) 2012 André Erdmann <dywi@mailerd.de>
# Distributed under the terms of the GNU General Public License;
# either version 2 of the License, or (at your option) any later version.

"""dependency environment

This module implements DepEnv, a dependency environment that is used during
dependency resolution. Typically, a DepEnv instance contains the original
dependency string to be looked up, its resolution progess ("to be resolved",
"is resolved, resolved by <>", "unresolvable") and some calculated data.
"""

__all__ = [ 'DepEnv', ]

import re

import roverlay.versiontuple

from roverlay import strutil

class DepEnv ( object ):
   """Dependency environment

   class-wide variables:
   * _NAME               -- a regex (string) that matches a dependency name,
                            e.g. "GDAL library"
   * _VER                -- a regex (string) that matches a dependency version,
                            e.g "1.4"
   * _VERMOD             -- a regex (string) that matches a dependency version
                            modifier, e.g. ">=" or "<"
   * VERSION_REGEX       -- a set of regexes (compiled) that match dependency
                            strings that can be used by fuzzy dependency
                            resolution
   * FIXVERSION_REGEX    -- a regex (compiled) used to replace R package
                            version separator chars '_', '-' with dots '.'.
   * URI_PURGE           -- a regex (compiled) that matches "useless" uri
                            statements from dependency strings, e.g.
                            "GDAL library from http://..." => "GDAL library"
   * WHITESPACE          -- a regex (compiled) that matches whitespace

   * TRY_ALL_REGEXES     -- a bool that controls whether _depsplit() should
                            stop after the first matching regex (which should
                            be fine since the regexes currently used are
                            mutually exclusive)

   class-wide integer variables used with bitwise operations:

   * STATUS_UNDONE       -- indicates that a DepEnv has to be processed
   * STATUS_RESOLVED     -- indicates that a DepEnv has been resolved
   * STATUS_UNRESOLVABLE -- indicates that a DepEnv is unresolvable
   """

   # excluding A-Z since dep_str_low will be used to find a match
   # _NAME ::= word{<whitespace><word>}
   _NAME = '(?P<name>[a-z0-9_\-/.:+-]+(\s+[a-z0-9_\-/.+-]+)*)'

   # _VER              ::= [[<version_separator>]*<digit>[<digit>]*]*
   # digit             ::= {0..9}
   # version_separator ::= {'.','_','-'}
   # examples: .9, 1.0-5, 3, 5..-_--2
   _VER  = '(?P<ver>[0-9._\-]+)'

   # { <, >, ==, <=, >=, =, != }
   _VERMOD = '(?P<vmod>[<>]|[=<>!]?[=])'

   _NAME_PREFIX = '(?P<name_prefix>for building from source[:])'
   _NAME_SUFFIX = '(?P<name_suffix>lib|library)'

   # integer representation of version modifiers
   ## duplicate of versiontuple.py
   VMOD_NONE  = roverlay.versiontuple.VMOD_NONE
   VMOD_UNDEF = roverlay.versiontuple.VMOD_UNDEF
   VMOD_NOT   = roverlay.versiontuple.VMOD_NOT
   VMOD_EQ    = roverlay.versiontuple.VMOD_EQ
   VMOD_NE    = roverlay.versiontuple.VMOD_NE
   VMOD_GT    = roverlay.versiontuple.VMOD_GT
   VMOD_GE    = roverlay.versiontuple.VMOD_GE
   VMOD_LT    = roverlay.versiontuple.VMOD_LT
   VMOD_LE    = roverlay.versiontuple.VMOD_LE

   VMOD = {
      '!=' : VMOD_NE,
      '='  : VMOD_EQ,
      #'==' : VMOD_EQ, # normalized by _depslit()
      '>'  : VMOD_GT,
      '>=' : VMOD_GE,
      '<'  : VMOD_LT,
      '<=' : VMOD_LE,
   }

   # name/version regexes used for fuzzy dep rules
   VERSION_REGEX = frozenset (
      re.compile ( r ) for r in ((
         # 'R >= 2.15', 'R >=2.15' etc. (but not 'R>=2.15'!)
         '^{prefix}?\s*{name}\s+{vermod}?\s*{ver}\s*{suffix}?\s*$'.format (
            name=_NAME, vermod=_VERMOD, ver=_VER,
            prefix=_NAME_PREFIX, suffix=_NAME_SUFFIX,
         ),

         # 'R (>= 2.15)', 'R(>=2.15)' etc.
         '^{prefix}?\s*{name}\s*\(\s*{vermod}?\s*{ver}\s*\)\s*{suffix}?$'.format (
            name=_NAME, vermod=_VERMOD, ver=_VER,
            prefix=_NAME_PREFIX, suffix=_NAME_SUFFIX,
         ),
         # 'R [>= 2.15]', 'R[>=2.15]' etc.
         '^{prefix}?\s*{name}\s*\[\s*{vermod}?\s*{ver}\s*\]\s*{suffix}?$'.format (
            name=_NAME, vermod=_VERMOD, ver=_VER,
            prefix=_NAME_PREFIX, suffix=_NAME_SUFFIX,
         ),

         # 'R {>= 2.15}', 'R{>=2.15}' etc.
         '^{prefix}?\s*{name}\s*\{{\s*{vermod}?\s*{ver}\s*\}}\s*{suffix}?$'.format (
            name=_NAME, vermod=_VERMOD, ver=_VER,
            prefix=_NAME_PREFIX, suffix=_NAME_SUFFIX,
         ),
      ))
   )

   FIXVERSION_REGEX = re.compile ( '[_\-]' )
   URI_PURGE        = re.compile ( '\s*from\s*(http|ftp|https)://[^\s]+' )
   WHITESPACE       = re.compile ( '\s+' )
   #AND_SPLIT        = re.compile ( '\s+and\s+|\s+&&\s+', flags=re.IGNORECASE )
   AND_SPLIT        = re.compile ( '\s+and\s+', flags=re.IGNORECASE )

   # try all version regexes if True, else break after first match
   TRY_ALL_REGEXES  = False

   STATUS_UNDONE       = 1
   STATUS_RESOLVED     = 2
   STATUS_UNRESOLVABLE = 4

   @classmethod
   def from_str ( cls, dep_str, deptype_mask, package_ref=None ):
      """Generator that (pre-)parses a dependency string and creates
      DepEnv objects for it.

      arguments:
      * dep_str      --
      * deptype_mask --
      * package_ref  --
      """
      # split dep_str into logically ANDed dependency strings,
      # unquote them, remove "from <uri>.." entries and replace all
      # whitespace by a single ' ' char
      for substring in cls.AND_SPLIT.split ( dep_str ):
         yield cls (
            dep_str = (
               cls.WHITESPACE.sub ( ' ',
                  cls.URI_PURGE.sub ( '',
                     strutil.unquote ( substring )
                  )
               ).strip()
            ),
            deptype_mask = deptype_mask,
            package_ref  = package_ref,
         )
   # --- end of from_str (...) ---

   def __init__ ( self, dep_str, deptype_mask, package_ref=None ):
      """Initializes a dependency environment that represents the dependency
      resolution of one entry in the description data of an R package.
      Precalculating most (if not all) data since this object will be passed
      through many dep rules.

      arguments:
      * dep_str    -- dependency string at it appears in the description data.
      * deptype_mask --
      * package_ref  --
      """
      self.deptype_mask = deptype_mask
      self.status       = DepEnv.STATUS_UNDONE
      self.resolved_by  = None

      self.package_ref  = package_ref
      if package_ref is not None:
         self.get_package_info = self._deref_package_info
         self.repo_id          = (
            package_ref.deref_safe().get ( 'origin' ).get_identifier()
         )
      else:
         self.get_package_info = self._deref_none
         self.repo_id          = None


      self.dep_str      = dep_str
      self.dep_str_low  = dep_str.lower()

      self.try_all_regexes = self.__class__.TRY_ALL_REGEXES

      self._depsplit()

      # (maybe) TODO: analyze dep_str: remove useless comments,...

   # --- end of __init__ (...) ---

   def _deref_none ( self ):
      return None
   # --- end of _deref_none (...) ---

   def _deref_package_info ( self ):
      return self.package_ref.deref_safe()
   # --- end of _deref_package_info (...) ---

   def _depsplit ( self ):
      result = list()
      for r in self.__class__.VERSION_REGEX:
         m = r.match ( self.dep_str_low )
         if m is not None:

            version = self.__class__.FIXVERSION_REGEX.sub (
               '.', m.group ( 'ver' )
            )
            # fix versions like ".9" (-> "0.9")
            if version [0] == '.': version = '0' + version

            vmod = m.group ( 'vmod' )

            if not vmod:
               # version required, but no modifier: set vmod to '>='
               vmod = '>='
            elif vmod == '==':
               # "normalize"
               vmod = '='

            version_strlist = version.split ( '.' )
            version_iparts  = list()

            for v in version_strlist:
               #i = None
               try:
                  i = int ( v )
                  version_iparts.append ( i )
               except ValueError:
                  v2 = v.partition ( '_' )[0].partition ( '-' ) [0]
                  version_iparts.append ( int ( v2 ) if v2 else 0 )


            result.append ( dict (
               name             = m.group ( 'name' ),
               name_low         = m.group ( 'name' ).lower(),
               version_modifier = vmod,
               version          = version,
               version_strlist  = version_strlist,
               version_tuple    = roverlay.versiontuple.IntVersionTuple (
                  version_iparts
               ),
               vmod             = self.VMOD.get ( vmod, self.VMOD_UNDEF ),
            ) )

            if not self.try_all_regexes: break

      if result:
         self.fuzzy = tuple ( result )
   # --- end of _depsplit (...) ---

   def set_resolved ( self, resolved_by, append=False ):
      """Marks this DepEnv as resolved with resolved_by as corresponding
      portage package.

      arguments:
      * resolved_by -- resolving portage package
      * append -- whether to append resolved_by or not; NOT IMPLEMENTED
      """
      if self.resolved_by is None:
         self.resolved_by = resolved_by
      elif append:
         # useful?
         raise Exception ( "appending is not supported..." )
      else:
         raise Exception (
            "dependency is already resolved and append is disabled."
         )

      # add RESOLVED status
      self.status |= DepEnv.STATUS_RESOLVED

   # --- end of set_resolved (...) ---

   def set_unresolvable ( self, force=False ):
      """Marks this DepEnv as unresolvable.

      arguments:
      force -- force unresolvable status even if this DepEnv
                is already resolved
      """
      if force or not self.status & DepEnv.STATUS_RESOLVED:
         self.resolved_by = None
         self.status |= DepEnv.STATUS_UNRESOLVABLE
      else:
         raise Exception ("dependency is already marked as resolved." )

   # --- end of set_unresolvable (...) ---

   def zap ( self ):
      """Resets the status of this DepEnv and clears out all resolving pkgs."""
      self.status      = DepEnv.STATUS_UNDONE
      self.resolved_by = None

   # --- end of zap (...) ---

   def is_resolved ( self ):
      """Returns True if this DepEnv is resolved, else false."""
      return bool ( self.status & DepEnv.STATUS_RESOLVED )

   # --- end of is_resolved (...) ---

   def get_result ( self ):
      """Returns the result of this DepEnv as a tuple
      ( original dep str, resolving portage package ) where resolving portage
      package may be None.
      """
      return ( self.dep_str, self.resolved_by )

   # --- end of get_result (...) ---

   def get_resolved ( self ):
      return self.resolved_by
   # --- end of get_resolved (...) ---

# --- end of DepEnv ---
