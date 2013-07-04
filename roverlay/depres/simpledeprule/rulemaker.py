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

from roverlay import config

from roverlay.depres import deptype
from roverlay.depres.simpledeprule import rules
from roverlay.depres.simpledeprule.abstractrules import *
from roverlay.depres.simpledeprule.pool import SimpleDependencyRulePool

class SimpleRuleMaker ( object ):

   def __init__ ( self, rule_separator=None ):
      self.logger = logging.getLogger ( self.__class__.__name__ )

      self.single_line_separator = re.compile (
         '\s+::\s+' if rule_separator is None else rule_separator
      )

      self.DEPTYPE_MAP = {
         'all'     : deptype.ALL,
         'sys'     : deptype.external,
         'pkg'     : deptype.internal,
         'selfdep' : deptype.selfdep,
      }

      self.multiline_start = '{'
      self.multiline_stop  = '}'
      self.comment_char    = '#'
      self.kw_selfdep_once = '@selfdep'
      self._kwmap          = rules.RuleConstructor (
         eapi = config.get_or_fail ( 'EBUILD.eapi' )
      )
      # deptype_kw is '#deptype' (this keyword requires comment 'mode')
      self.deptype_kw      = 'deptype'
      self._deptype        = deptype.ALL
      self._deptype_once   = deptype.NONE
      self._next           = None
      # [ ( deptype, rule ), ... ]
      self._rules          = list()
   # --- end of __init__ (...) ---

   def zap ( self ):
      if self._next is not None:
         self.logger.warning (
            "Multi line rule does not end at EOF - ignored"
         )
      self._next         = None
      self._rules        = list()
   # --- end of zap (...) ---

   def done ( self, as_pool=False ):
      rule_count = len ( self._rules )
      if as_pool:
         poolmap = dict()
         for dtype, rule in self._rules:
            if dtype not in poolmap:
               poolmap [dtype] = SimpleDependencyRulePool (
                  name=str ( id ( self ) ),
                  deptype_mask=dtype
               )
            poolmap [dtype].add ( rule )
         ret = ( rule_count, tuple ( poolmap.values() ) )
      else:
         ret = self._rules
      self.zap()
      return ret
   # --- end of done (...) ---

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
      if self._deptype_once is not deptype.NONE:
         if clear_temporary:
            ret = self._deptype_once
            self._deptype_once = deptype.NONE
            return ret
         else:
            self._deptype_once
      else:
         return self._deptype
   # --- end of _get_effective_deptype (...) ---

   def _single_line_rule ( self, dep, dep_str='' ):
      # single line rule, either selfdep,
      #  e.g. '~zoo' -> fuzzy sci-R/zoo :: zoo
      #  or normal rule 'dev-lang/R :: R'
      # selfdeps are always single line statements (!)

      rule_deptype                  = self._get_effective_deptype()
      rule_class, resolving, kwargs = self._kwmap.lookup ( dep )

      if dep_str:
         # normal rule
         new_rule = rule_class (
            resolving_package = resolving,
            dep_str           = dep_str,
            is_selfdep        = (
               1 if ( rule_deptype & deptype.selfdep ) else 0
            ),
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
      self._rules.append ( ( rule_deptype, new_rule ) )
      return True
   # --- end of _single_line_rule (...) ---

   def add ( self, line ):
      if len ( line ) == 0:
         return True
      elif self._next is not None:
         if line [0] == self.multiline_stop:
            # end of a multiline rule,
            #  add rule to rules and set next_rule to None
            self._next [1].done_reading()
            self._rules.append ( self._next )
            self._next = None
         else:
            # new resolved str
            self._next [1].add_resolved ( line )

         return True

      elif line [0] == self.comment_char:
         if line [ 1 : 1 + len ( self.deptype_kw ) ] == self.deptype_kw :
            # changing deptype ("#deptype <type>")
            dtype_str = line [ len ( self.deptype_kw ) + 2 : ].lstrip().lower()
            self._deptype = self._parse_deptype ( dtype_str )

         # else is a comment,
         #  it's intented that multi line rules cannot contain comments
         return True

      elif line == self.kw_selfdep_once:
         self._deptype_once = self._deptype | deptype.selfdep
         return True

      elif len ( line ) > 1 and line [-1] == self.multiline_start:
         l = line [:-1].rstrip()
         rule_class, resolving, kwargs = self._kwmap.lookup ( l )

         self._next = (
            self._get_effective_deptype(),
            rule_class ( resolving_package=resolving, **kwargs ),
         )
         return True

      else:
         return self._single_line_rule (
            *self.single_line_separator.split ( line, 1  )
         )
   # --- end of add (...) ---
