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
   'RDEPEND', 'R_SUGGESTS', 'SRC_URI', 'KEYWORDS',
]

import roverlay.strutil

from roverlay.ebuild.abstractcomponents import ListValue, EbuildVar, get_value_str

IUSE_SUGGESTS = 'R_suggests'
RSUGGESTS_NAME = IUSE_SUGGESTS.upper()

# ignoring style guide here (camel case, ...)

class DESCRIPTION ( EbuildVar ):
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


class KEYWORDS ( EbuildVar ):
   """A KEYWORDS="amd64 -x86 ..." statement."""
   def __init__ ( self, keywords ):
      super ( KEYWORDS, self ).__init__ (
         name=self.__class__.__name__,
         value=keywords,
         priority=80
      )
   # --- end of __init__ (...) ---


class SRC_URI_ListValue ( ListValue ):
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
         get_value_str (
            (
               "{} -> {}".format ( v[0], v[1] ) if v[1] else str ( v[0] )
            ),
            quote_char=( "'" if quoted else None )
         ) for v in self.value
      )
   # --- end of join_value_str (...) ---


class SRC_URI ( EbuildVar ):
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


class IUSE ( EbuildVar ):
   """An IUSE="..." statement."""
   def __init__ ( self, use_flags=None, using_suggests=False ):
      """An IUSE="..." statement.

      arguments:
      * use_flags      -- IUSE value
      * using_suggests -- if True: enable R_Suggests USE flag
      """
      super ( IUSE, self ) . __init__ (
         name='IUSE',
         value=ListValue ( use_flags, empty_value='${IUSE:-}' ),
         priority=130,
         param_expansion=True
      )
      self.value.single_line = True
      if using_suggests:
         self.add_value ( IUSE_SUGGESTS )


class R_SUGGESTS ( EbuildVar ):
   """A R_SUGGESTS="..." statement."""
   def __init__ ( self, deps, **kw ):
      super ( R_SUGGESTS, self ) . __init__ (
         name=RSUGGESTS_NAME,
         value=ListValue ( deps ),
         priority=140,
      )


class DEPEND ( EbuildVar ):
   """A DEPEND="..." statement."""
   def __init__ ( self, deps, **kw ):
      super ( DEPEND, self ) . __init__ (
         name='DEPEND',
         value=ListValue ( deps ),
         priority=150,
         param_expansion=True,
      )


class RDEPEND ( EbuildVar ):
   """A RDEPEND="..." statement."""
   def __init__ ( self, deps, using_suggests=False, **kw ):
      super ( RDEPEND, self ) . __init__ (
         name='RDEPEND',
         value=ListValue ( deps, empty_value="${DEPEND:-}" ),
         priority=160,
         param_expansion=True
      )
      if using_suggests: self.enable_suggests()

   def enable_suggests ( self ):
      """Adds the optional R_SUGGESTS dependencies to RDEPEND."""
      self.add_value ( '{USE}? ( ${{{DEPS}}} )'.format (
         USE  = IUSE_SUGGESTS,
         DEPS = RSUGGESTS_NAME
      ) )


class MISSINGDEPS ( EbuildVar ):
   def __init__ ( self, missing_deps, do_sort=False, **kw ):
      super ( MISSINGDEPS, self ) . __init__ (
         name            = '_UNRESOLVED_PACKAGES',
         value           = ListValue (
            missing_deps if not do_sort \
               else tuple ( sorted ( missing_deps, key=lambda s : s.lower() ) ),
            bash_array=True
         ),
         priority        = 200,
         param_expansion = None,
      )
