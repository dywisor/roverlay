# R overlay -- simple dependency rules, dynamic selfdep pool
# -*- coding: utf-8 -*-
# Copyright (C) 2012 André Erdmann <dywi@mailerd.de>
# Distributed under the terms of the GNU General Public License;
# either version 2 of the License, or (at your option) any later version.

"""dynamic selfdep pool

This module provides a class, DynamicSelfdepRulePool, that creates dynamic
(i.e. exist only in memory, not as file) dependency rules that resolve
dependencies on other R packages ("sci-R/<pkg>" if OVERLAY_CATEGORY is sci-R).
The rules are created by using a "rule keyword function" (a function/generator
that yields keywords for rule creation), typically provided by the overlay
package's "root" module.
The DynamicSelfdepRulePool is strict about matches; it only matches strings
whose dependency type contains deptype.internal.
"""

__all__ = [ 'DynamicSelfdepRulePool', 'get' ]

from roverlay.depres import deptype
from roverlay.depres.simpledeprule.pool import SimpleDependencyRulePool
from roverlay.depres.simpledeprule.rules import SimpleFuzzyDependencyRule

class DynamicSelfdepRulePool ( SimpleDependencyRulePool ):
   """A rule pool that gets its rules from a function."""

   def __init__ ( self, rule_kw_function, rule_class, priority=120, **kwargs ):
      super ( DynamicSelfdepRulePool, self ). __init__ (
         name='dynamic selfdeps', priority=priority,
         deptype_mask=deptype.internal,
         **kwargs
      )

      self._rule_class       = rule_class
      self._rule_kw_function = rule_kw_function
   # --- end of __init__ (...) ---

   def accepts ( self, deptype_mask, try_other=False ):
      if try_other:
         # never resolve external deps as selfdeps
         return False
      else:
         return self.deptype_mask & deptype_mask
   # --- end of accepts (...) ---

   def reload ( self ):
      self.rules = list (
         self._rule_class ( is_selfdep=True, **kwargs ) \
            for kwargs in self._rule_kw_function()
      )
   # --- end of reload (...) ---


def get ( rule_kw_function ):
   """Returns a default DynamicSelfdepRulePool for rule_kw_function."""
   return DynamicSelfdepRulePool (
      rule_kw_function, SimpleFuzzyDependencyRule
   )
# --- end of get (...) ---
