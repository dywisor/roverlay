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

import collections

from roverlay.depres import deptype
from roverlay.depres.deprule import DynamicDependencyRulePool
from roverlay.depres.simpledeprule.rules import SimpleFuzzyDependencyRule

class DynamicSelfdepRulePool ( DynamicDependencyRulePool ):
   """A rule pool that gets its rules from a function."""

   def __init__ ( self, rule_generator, rule_class, priority=120, **kwargs ):
      super ( DynamicSelfdepRulePool, self ). __init__ (
         name='dynamic selfdeps', priority=priority,
         deptype_mask=deptype.internal,
         **kwargs
      )

      self.rules           = None
      self._rule_generator = rule_generator
      self.set_rule_class ( rule_class )
   # --- end of __init__ (...) ---

   def sort_rules ( self ):
      # TODO: sort self.rules itself ("sort repos")
      priokey = lambda k: k.priority

      if self.rules:
         for rules in self.rules.values():
            rules.sort ( key=priokey )
   # --- end of sort_rules (...) ---

   def iter_rules ( self ):
      if self.rules:
         for rules in self.rules.values():
            for rule in rules:
               yield rule
   # --- end of iter_rules (...) ---

   def iter_rules_resolving ( self, dep_env ):
      specific_rules = self.rules.get ( dep_env.repo_id, None )
      if specific_rules is not None:
         for rule in specific_rules:
            yield rule

      for rules in self.rules.values():
         if rules is not specific_rules:
            for rule in rules:
               yield rule
   # --- end of iter_rules_resolving (...) ---

   def set_rule_class ( self, rule_class ):
      self._rule_generator.rule_class = rule_class
   # --- end of set_rule_class (...) ---

   def accepts_other ( self, dep_env ):
      # never resolve external deps as selfdeps
      return False
   # --- end of accepts_other (...) ---

   def reload ( self ):
      self.rules = self._rule_generator.make_rule_dict()
   # --- end of reload (...) ---


# --- end of DynamicSelfdepRulePool ---


def get ( rule_kw_function ):
   """Returns a default DynamicSelfdepRulePool for rule_kw_function."""
   return DynamicSelfdepRulePool (
      rule_kw_function, SimpleFuzzyDependencyRule
   )
# --- end of get (...) ---
