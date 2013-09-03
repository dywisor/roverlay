# R overlay -- dependency resolution, basic dependency rules
# -*- coding: utf-8 -*-
# Copyright (C) 2012 André Erdmann <dywi@mailerd.de>
# Distributed under the terms of the GNU General Public License;
# either version 2 of the License, or (at your option) any later version.

"""basic dependency rules"""

__all__ = [ 'DependencyRule', 'DependencyRulePool', ]

import roverlay.util.objects

import roverlay.depres.depresult

from roverlay.depres import deptype

class DependencyRule ( object ):
   """Prototype of a dependency rule. Not meant for instantiation."""

   def __init__ ( self, priority ):
      """Initializes an rule pool.

      arguments:
      * priority -- used for sorting rule pools, lower means more important
      """
      super ( DependencyRule, self ).__init__()
      self.max_score = 1000
      self.priority  = priority
   # --- end of __init__ (...) ---

   def matches ( self, dep_env ):
      """Returns a tuple ( score ::= int > 0, matching dep ::= DepResult )
      if this rule matches the given DepEnv, else None"""
      return None
   # --- end of matches (...) ---

   def _make_result ( self, resolved_dep, score, *args, **kw ):
      return roverlay.depres.depresult.DepResult (
         resolved_dep, score, self, *args, **kw
      )
   # --- end of _make_result (...) ---

   make_result = _make_result

   def export_rule ( self ):
      raise NotImplementedError()
   # --- end of export_rule (...) ---

# --- end of DependencyRule ---


class DependencyRulePoolBase ( object ):
   """Base object for dependency rule pools."""

   def __init__ ( self, name, priority, deptype_mask ):
      super ( DependencyRulePoolBase, self ).__init__()
      self.name = name
      self.priority = priority
      # filter out deptype flags like "mandatory"
      self.deptype_mask = deptype_mask & deptype.RESOLVE_ALL

      # the "rule weight" is the sum of the rules' priorities
      #  it's used to compare/sort dependency pools with
      #  the same priority (lesser weight is better)
      self.rule_weight  = 0
   # --- end of __init__ (...) ---

   def empty ( self ):
      """Returns True if this pool has no rules."""
      for rule in self.iter_rules():
         return False
      return True
   # --- end of empty (...) ---

   @roverlay.util.objects.abstractmethod
   def sort_rules ( self ):
      pass
   # --- end of sort_rules (...) ---

   def sort ( self ):
      """Sorts this rule pool and determines its weight which is used
      to compare rule pools.
      """
      self.sort_rules()
      self.set_rule_weight()
   # --- end of sort (...) ---

   @roverlay.util.objects.abstractmethod
   def iter_rules ( self ):
      return
   # --- end of iter_rules (...) ---

   @roverlay.util.objects.abstractmethod ( params=[ 'dep_env' ] )
   def iter_rules_resolving ( self, dep_env ):
      pass
   # --- end of iter_rules_resolving (...) ---

   def get_all_matches ( self, dep_env ):
      for rule in self.iter_rules_resolving ( dep_env ):
         result = rule.matches ( dep_env )
         if result:
            yield result
   # --- end of get_all_matches (...) ---

   def matches ( self, dep_env ):
      for rule in self.iter_rules_resolving ( dep_env ):
         result = rule.matches ( dep_env )
         if result:
            return result
      return None
   # --- end of matches (...) ---

   def matches_all ( self, dep_env, skip_matches=0 ):
      """Tries to find a match in this dependency rule pool.
      The first match is immediatly returned unless skip_matches is != 0, in
      which case the first (>0) / last (<0) skip_matches matches are skipped.
      Returns a tuple ( score, portage dependency ),
      e.g. ( 1000, 'sys-apps/which' ), if match found, else None.

      arguments:
      * dep_env -- dependency to look up
      * skip_matches --
      """

      if abs ( skip_matches ) >= len ( self.rules ):
         # all potential matches ignored,
         #  cannot expect a result in this case - abort now
         pass

      elif skip_matches >= 0:
         skipped = 0
         for result in self.get_all_matches ( dep_env ):
            if skipped < skip_matches:
               skipped += 1
            else:
               return result

      else:
         matches = list ( self.get_all_matches() )
         try:
            return matches [skip_matches]
         except IndexError:
            pass

      # default return
      return None
   # --- end of matches_all (...) ---

   def set_rule_weight ( self ):
      priosum = 0
      for rule in self.iter_rules():
         priosum += rule.priority
      self.rule_weight = priosum
      return self.rule_weight
   # --- end of set_rule_weight (...) ---

   def accepts_mask ( self, deptype_mask ):
      """Returns True if this pool accepts the given deptype_mask."""
      return bool ( self.deptype_mask & deptype_mask )
   # --- end of accepts_mask (...) ---

   def accepts ( self, dep_env ):
      """Returns True if this pool accepts the given dep env."""
      return bool ( self.deptype_mask & dep_env.deptype_mask )
   # --- end of accepts (...) ---

   @roverlay.util.objects.abstractmethod
   def accepts_other ( self, dep_env ):
      """Returns True if this pool can be used to resolve a dep env whose
      deptype mask is rejected by this pool.
      (Not necessarily the inverse of accepts().)
      """
      pass
   # --- end of accepts_other (...) ---

   def export_rules ( self ):
      """Exports all rules. Typically, this generates text lines."""
      for rule in self.iter_rules():
         for item in rule.export_rule():
            yield item
   # --- end of export_rules (...) ---

   def export_rules_into ( self, fh ):
      """Writes all rules into the given file handle.

      arguments:
      * fh --
      """
      NL = '\n'
      for item in self.export_rules():
         fh.write ( str ( item ) )
         fh.write ( NL )
   # --- end of exports_rules_into (...) ---

# --- end of DependencyRulePoolBase ---


class DependencyRulePool ( DependencyRulePoolBase ):

   def __init__ ( self, name, priority, deptype_mask, initial_rules=None ):
      """Initializes an DependencyRulePool, which basically is a set of
      dependency rules with methods like "search for x in all rules."

      arguments:
      * name -- name of this rule pool
      * priority -- priority of this pool (lower is better)
      """
      super ( DependencyRulePool, self ).__init__(
         name, priority, deptype_mask
      )
      if initial_rules is None:
         self.rules = list()
      else:
         self.rules = list ( initial_rules )
      self._rule_add    = self.rules.append
   # --- end of __init__ (...) ---

   def iter_rules ( self ):
      return iter ( self.rules )
   # --- end of iter_rules (...) ---

   def iter_rules_resolving ( self, dep_env ):
      return iter ( self.rules )
   # --- end of iter_rules_resolving (...) ---

   def empty ( self ):
      """Returns True if this pool has no rules."""
      return len ( self.rules ) == 0
   # --- end of empty (...) ---

   def sort_rules ( self ):
      """Sorts this rule pool and determines its weight which is used
      to compare rule pools.
      """
      self.rules.sort ( key=lambda rule : rule.priority )
   # --- end of sort_rules (...) ---

   def accepts_other ( self, dep_env ):
      """Returns True if this pool can be used to resolve a dep env whose
      deptype mask is rejected by this pool.
      (Not necessarily the inverse of accepts().)
      """
      return not self.accepts ( dep_env )
   # --- end of accepts_other (...) ---

   def add ( self, rule ):
      """Adds a DependencyRule to this rule pool.

      arguments:
      * rule --
      """
      if issubclass ( rule, DependencyRule ):
         self._rule_add ( rule )
      else:
         raise Exception ( "bad usage (dependency rule expected)." )

      return None
   # --- end of add (...) ---

# --- end of DependencyRulePool ---


class DynamicDependencyRulePool ( DependencyRulePoolBase ):

   def accepts_other ( self, dep_env ):
      return False
   # --- end of accepts_other (...) ---

   @roverlay.util.objects.abstractmethod
   def reload_rules ( self ):
      pass
   # --- end of reload_rules (...) ---

   def reload ( self ):
      self.reload_rules()
      self.sort()
   # --- end of reload (...) ---

# --- end of DynamicDependencyRulePool ---
