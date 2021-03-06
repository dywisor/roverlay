# R overlay -- simple dependency rules, rule maker
# -*- coding: utf-8 -*-
# Copyright (C) 2012 André Erdmann <dywi@mailerd.de>
# Distributed under the terms of the GNU General Public License;
# either version 2 of the License, or (at your option) any later version.

"""rule maker

Thos module provides a class, SimpleRuleMaker, that converts string input
(text lines, e.g. from file or stdin) into dependency rules.
"""

__all__ = [ 'SimpleRuleMaker', ]

import re
import logging

import roverlay.util.mapreader

from roverlay import config

from roverlay.depres import deptype
from roverlay.depres.simpledeprule import rules
from roverlay.depres.simpledeprule.pool import SimpleDependencyRulePool

class SimpleRuleMaker ( roverlay.util.mapreader.MapFileParser ):

   breakparse = frozenset ({ '! NOPARSE', '! BREAK' })
   kw_error   = frozenset ({ '! ERROR', })

   def __init__ ( self, rule_separator=None ):
      super ( SimpleRuleMaker, self ).__init__()
      self.logger = logging.getLogger ( self.__class__.__name__ )

      self.DEPTYPE_MAP = {
         'none'    : 0,
         'all'     : deptype.ALL,
         'sys'     : deptype.external,
         'pkg'     : deptype.internal,
         'selfdep' : deptype.selfdep,
      }

      self.kw_selfdep_once = '@selfdep'
      self._kwmap          = rules.RuleConstructor (
         eapi = config.get_or_fail ( 'EBUILD.eapi' )
      )
      # deptype_kw is '#deptype' (this keyword requires comment 'mode')
      self.deptype_kw      = 'deptype'
      self._deptype        = deptype.ALL
      self._deptype_once   = deptype.NONE
      self.file_count      = 0
   # --- end of __init__ (...) ---

   def has_context ( self ):
      return (
         self._deptype_once != deptype.NONE
         or self._next is not None
      )
   # --- end of has_context (...) ---

   def read_lines_begin ( self ):
      # reset deptype
      self._deptype      = deptype.ALL
      self._deptype_once = deptype.NONE
   # --- end of read_lines_begin (...) ---

   def read_file_done ( self, filepath ):
      self.file_count += 1
   # --- end of read_file_done (...) ---

   def make_result ( self, as_pool=False ):
      rule_count = len ( self._items )
      if as_pool:
         poolmap = dict()
         for dtype, rule in self._items:
            if dtype not in poolmap:
               poolmap [dtype] = SimpleDependencyRulePool (
                  name=str ( id ( self ) ),
                  deptype_mask=dtype
               )
            poolmap [dtype].add ( rule )
         return ( rule_count, tuple ( poolmap.values() ) )
      else:
         return self._items
   # --- end of make_result (...) ---

   def _parse_deptype ( self, deptype_str ):
      ret = deptype.NONE
      try:
         for item in deptype_str.split ( ',' ):
            ret |= self.DEPTYPE_MAP [item]
      except KeyError:
         raise Exception ( "unknown deptype {!r}".format ( deptype_str ) )

      return ret if ret != deptype.NONE else deptype.ALL
   # --- end of _parse_deptype (...) ---

   def _get_effective_deptype ( self, clear_temporary=True ):
      """Returns a 2-tuple ( <deptype>, <deptype_is_selfdep> ) based on
      self._deptype and self._deptype_once. deptype_is_selfdep is an int
      (0 or 1), "true" selfdeps (2) cannot be recognized here.

      arguments:
      * clear_temporary -- clear self._deptype_once
      """
      if self._deptype_once is not deptype.NONE:
         ret = self._deptype_once
         if clear_temporary:
            self._deptype_once = deptype.NONE
      else:
         ret = self._deptype

      return ( ret, 1 if ( ret & deptype.selfdep ) else 0 )
   # --- end of _get_effective_deptype (...) ---

   def handle_entry_line ( self, dep, dep_str='' ):
      # single line rule, either selfdep,
      #  e.g. '~zoo' -> fuzzy sci-R/zoo :: zoo
      #  or normal rule 'dev-lang/R :: R'
      # selfdeps (rule stubs) are always single line statements (!)

      rule_deptype, is_selfdep      = self._get_effective_deptype()
      rule_class, resolving, kwargs = self._kwmap.lookup ( dep )

      if dep_str:
         # normal rule
         new_rule = rule_class (
            resolving_package = resolving,
            dep_str           = dep_str,
            is_selfdep        = is_selfdep,
            **kwargs
         )

      elif resolving is not None:
         # selfdep (rule stub)
         dep_str   = resolving
         resolving = (
            config.get_or_fail ( 'OVERLAY.category' ) + '/' + resolving
         )

         new_rule = rule_class (
            resolving_package = resolving,
            dep_str           = dep_str,
            is_selfdep        = 2,
            **kwargs
         )
      else:
         return False

      new_rule.done_reading()
      self._items.append ( ( rule_deptype, new_rule ) )
      return True
   # --- end of handle_entry_line (...) ---

   def handle_multiline_begin ( self, line ):
      rule_deptype, is_selfdep      = self._get_effective_deptype()
      rule_class, resolving, kwargs = self._kwmap.lookup ( line )

      self._next = (
         rule_deptype,
         rule_class (
            resolving_package = resolving,
            is_selfdep        = is_selfdep,
            **kwargs
         ),
      )
      return True
   # --- end of handle_multiline_begin (...) ---

   def handle_multiline_end ( self, line ):
      self._next [1].done_reading()
      self._items.append ( self._next )
      self._next = None
      return True
   # --- end of handle_multiline_end (...) ---

   def handle_multiline_append ( self, line ):
      self._next [1].add_resolved ( line )
      return True
   # --- end of handle_multiline_append (...) ---

   def handle_comment_line ( self, line ):
      if line[:len ( self.deptype_kw ) ] == self.deptype_kw:
         # changing deptype ("#deptype <type>")
         dtype_str = line.partition ( ' ' )[2].lower()
         self._deptype = self._parse_deptype ( dtype_str )

      elif line in self.breakparse:
         self.stop_reading = True

      elif line in self.kw_error:
         self.stop_reading = True
         raise Exception ( "#! ERROR" )

      # else is a "real" comment
      return True
   # --- end of handle_comment_line (...) ---

   def handle_option_line ( self, line ):
      if line == self.kw_selfdep_once:
         self._deptype_once = self._deptype | deptype.selfdep
         return True
      else:
         return False
   # --- end of handle_option_line (...) ---


# --- end of SimpleRuleMaker ---
