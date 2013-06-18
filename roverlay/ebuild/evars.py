# R overlay -- ebuild creation, ebuild variables
# -*- coding: utf-8 -*-
# Copyright (C) 2012 André Erdmann <dywi@mailerd.de>
# Distributed under the terms of the GNU General Public License;
# either version 2 of the License, or (at your option) any later version.

"""ebuild variables

This module implements all used ebuild variables (e.g. DEPEND, SRC_URI)
as classes.
These variables have different properties, e.g. DESCRIPTION's string is cut
after n (50) chars, RDEPEND is only printed if not empty and MISSINGDEPS
is printed as bash array.
"""

__all__ = [ 'DEPEND', 'DESCRIPTION', 'IUSE', 'MISSINGDEPS',
   'RDEPEND', 'R_SUGGESTS', 'R_SUGGESTS_USE_EXPAND', 'SRC_URI', 'KEYWORDS',
]

import collections
import re

import roverlay.strutil

import roverlay.ebuild.abstractcomponents

from roverlay.ebuild.abstractcomponents import ListValue

RSUGGESTS_NAME = 'R_SUGGESTS'

# ignoring style guide here (camel case, ...)


class UseExpandListValue (
   roverlay.ebuild.abstractcomponents.AbstractListValue
):
   """List value that represents USE_EXPAND-conditional depend atoms."""

   RE_USENAME = re.compile (
      (
         '(?P<prefix>.*[/])?'
         '(?P<pf>'
            '((?P<pn>.*)(?P<pvr>[-][0-9].*([-]r[0-9]+)?))'
         '|.*)'
      )
   )

   def __init__ (
      self, basename, deps, alias_map=None, indent_level=1, **kw
   ):
      super ( UseExpandListValue, self ).__init__ (
         indent_level = indent_level,
         empty_value  = None,
         bash_array   = False,
         **kw
      )
      self.insert_leading_newline = True
      self.alias_map              = alias_map or None
      self.basename               = basename.rstrip ( '_' ).lower()
      self.sort_flags             = True

      self.set_value ( deps )
   # --- end of __init__ (...) ---

   def _get_depstr_key ( self, depstr ):
      # tries to get the use flag name from depstr
      match = self.__class__.RE_USENAME.match ( depstr )
      if match:
         return self._get_use_key (
            ( match.group ( "pn" ) or match.group ( "pf" ) ).lower()
         )
      else:
         raise ValueError (
            "depstr {!r} cannot be parsed".format ( depstr )
         )
   # --- end of _get_depstr_key (...) ---

   def _get_use_key ( self, orig_key ):
      if self.alias_map:
         return self.alias_map.get ( orig_key, orig_key ).lower()
      else:
         return orig_key.lower()
   # --- end of _get_use_key (...) ---

   def _accept_value ( self, value ):
      if hasattr ( value, '__iter__' ):
         if isinstance ( value, str ):
            raise ValueError ( "x" )
      else:
         return False
   # --- end of _accept_value (...) ---

   def set_value ( self, deps ):
      self.depdict = dict()
      if deps: self.add ( deps )
   # --- end of set_value (...) ---

   def add ( self, deps ):
      assert not isinstance ( deps, str )

      for item in deps:
         if hasattr ( item, '__iter__' ) and not isinstance ( item, str ):
            key = self._get_use_key ( str ( item [0] ) )
            val = item [1]
         else:
            key = self._get_depstr_key ( item )
            val = item
         # -- end if;

         vref = self.depdict.get ( key, None )
         if vref is None:
            self.depdict [key] = [ val ]
         else:
            vref.append ( val )
         # -- end if;
   # --- end of add (...) ---

   def get_flag_names ( self ):
      return self.depdict.keys()
   # --- end of get_flags (...) --

   def get_flags ( self ):
      prefix = self.basename + '_'
      for flagname in self.depdict.keys():
         yield prefix + flagname
   # --- end of get_flags (...) ---

   def __len__ ( self ):
      return (
         self.depcount if hasattr ( self, 'depcount' )
         else len ( self.depdict )
      )
   # --- end of __len__ (...) ---

   def cleanup ( self ):
      depcount = 0
      delkeys  = set()
      for k, v in self.depdict.items():
         if v:
            depcount += len ( v )
         else:
            delkeys.add ( k )
      # -- end for

      for k in delkeys:
         del self.depdict [k]

      self.depcount = depcount
   # --- end of cleanup (...) ---

   def join_value_str ( self, join_str, quoted=False ):
      # get_value_str() not necessary here
      if self.sort_flags:
         return join_str.join (
            "{basename}_{flag}? ( {deps} )".format (
               basename=self.basename, flag=k, deps=' '.join ( v )
            ) for k, v in sorted (
               self.depdict.items(), key=( lambda item : item[0] )
            )
         )
      else:
         return join_str.join (
            "{basename}_{flag}? ( {deps} )".format (
               basename=self.basename, flag=k, deps=' '.join ( v )
            ) for k, v in self.depdict.items()
         )
   # --- end of join_value_str (...) ---

   def to_str ( self ):
      self.cleanup()
      return self._get_sh_list_str()
   # --- end of to_str (...) ---

# --- end of UseExpandListValue ---


class DESCRIPTION ( roverlay.ebuild.abstractcomponents.EbuildVar ):
   """A DESCRIPTION="..." statement."""

   SEE_METADATA = '... (see metadata)'

   def __init__ ( self, description, maxlen=None ):
      """A DESCRIPTION="..." statement. Long values will be truncated.

      arguments:
      * description -- description text
      * maxlen      -- maximum value length (>0, defaults to 50 chars)
      """
      assert maxlen is None or maxlen > 0

      super ( DESCRIPTION, self ) . __init__ (
         name='DESCRIPTION',
         value=description,
         priority=80, param_expansion=False
      )
      self.maxlen = maxlen or 50
   # --- end of __init__ (...) ---

   def _transform_value_str ( self, _str ):
      return roverlay.strutil.shorten_str (
         _str,
         self.maxlen,
         self.SEE_METADATA
      )
   # --- end of _transform_value_str (...) ---


class KEYWORDS ( roverlay.ebuild.abstractcomponents.EbuildVar ):
   """A KEYWORDS="amd64 -x86 ..." statement."""
   def __init__ ( self, keywords ):
      super ( KEYWORDS, self ).__init__ (
         name=self.__class__.__name__,
         value=keywords,
         priority=80
      )
   # --- end of __init__ (...) ---


class SRC_URI_ListValue ( roverlay.ebuild.abstractcomponents.ListValue ):
   """List value that represents SRC_URI entries."""

   def _accept_value ( self, value ): raise NotImplementedError()

   def add ( self, value ):
      """Adds/Appends a value."""
      if value [0]:
         self.value.append ( value )
      else:
         raise ValueError ( value )
   # --- end of add (...) ---

   def join_value_str ( self, join_str, quoted=False ):
      return join_str.join (
         roverlay.ebuild.abstractcomponents.get_value_str (
            (
               "{} -> {}".format ( v[0], v[1] ) if v[1] else str ( v[0] )
            ),
            quote_char=( "'" if quoted else None )
         ) for v in self.value
      )
   # --- end of join_value_str (...) ---


class SRC_URI ( roverlay.ebuild.abstractcomponents.EbuildVar ):
   """A SRC_URI="..." statement."""
   def __init__ ( self, src_uri, src_uri_dest ):
      super ( SRC_URI, self ) . __init__ (
         name     = 'SRC_URI',
         value    = SRC_URI_ListValue ( value=( src_uri, src_uri_dest ) ),
         priority = 90
      )

   def _empty_str ( self ):
      """Called if this SRC_URI evar has no uri stored."""
      return 'SRC_URI=""\nRESTRICT="fetch"'


class IUSE ( roverlay.ebuild.abstractcomponents.EbuildVar ):
   """An IUSE="..." statement."""
   def __init__ ( self, use_flags=None ):
      """An IUSE="..." statement.

      arguments:
      * use_flags      -- IUSE value
      * using_suggests -- if True: enable R_Suggests USE flag
      """
      super ( IUSE, self ) . __init__ (
         name='IUSE',
         value=ListValue ( use_flags, empty_value='${IUSE-}' ),
         priority=130,
         param_expansion=True
      )
      self.value.single_line = True


class R_SUGGESTS_USE_EXPAND ( roverlay.ebuild.abstractcomponents.EbuildVar ):
   """A R_SUGGESTS="..." statement with USE_EXPAND support."""

   def __init__ ( self, use_expand_name, deps, use_expand_map=None, **kw ):
      super ( R_SUGGESTS_USE_EXPAND, self ).__init__ (
         name=RSUGGESTS_NAME,
         value=UseExpandListValue (
            basename=use_expand_name, deps=deps, alias_map=use_expand_map
         ),
         priority=140,
      )
   # --- end of __init__ (...) ---

   def get_use_expand_name ( self ):
      return self.value.basename.upper()
   # --- end of get_use_expand_name (...) ---

   def get_flag_names ( self, *args, **kwargs ):
      return self.value.get_flag_names ( *args, **kwargs )
   # --- end of get_flag_names (...) ---

   def get_flags ( self, *args, **kwargs ):
      return self.value.get_flags ( *args, **kwargs )
   # --- end of get_flags (...) ---

class DEPEND ( roverlay.ebuild.abstractcomponents.EbuildVar ):
   """A DEPEND="..." statement."""
   def __init__ ( self, deps, **kw ):
      super ( DEPEND, self ) . __init__ (
         name='DEPEND',
         value=ListValue ( deps ),
         priority=150,
         param_expansion=True,
      )


class RDEPEND ( roverlay.ebuild.abstractcomponents.EbuildVar ):
   """A RDEPEND="..." statement."""
   def __init__ ( self, deps, using_suggests=False, **kw ):
      super ( RDEPEND, self ) . __init__ (
         name='RDEPEND',
         value=ListValue ( deps, empty_value="${DEPEND-}" ),
         priority=160,
         param_expansion=True
      )
      if using_suggests: self.enable_suggests()

   def enable_suggests ( self ):
      """Adds the optional R_SUGGESTS dependencies to RDEPEND."""
      self.add_value ( '${' + RSUGGESTS_NAME + '-}' )
   # --- end of enable_suggests (...) --


class MISSINGDEPS ( roverlay.ebuild.abstractcomponents.EbuildVar ):
   def __init__ ( self, missing_deps, do_sort=False, **kw ):
      super ( MISSINGDEPS, self ) . __init__ (
         name            = '_UNRESOLVED_PACKAGES',
         value           = ListValue (
            (
               missing_deps if not do_sort
               else sorted ( missing_deps, key=lambda s : s.lower() )
            ),
            bash_array=True
         ),
         priority        = 200,
         param_expansion = None,
      )
