# R overlay -- dependency resolution, basic dependency rules
# -*- coding: utf-8 -*-
# Copyright (C) 2012 André Erdmann <dywi@mailerd.de>
# Distributed under the terms of the GNU General Public License;
# either version 2 of the License, or (at your option) any later version.

"""basic dependency rules"""

__all__ = [ 'DependencyRule', 'DependencyRulePool', ]

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


class DependencyRulePool ( object ):

   def __init__ ( self, name, priority, deptype_mask, initial_rules=None ):
      """Initializes an DependencyRulePool, which basically is a set of
      dependency rules with methods like "search for x in all rules."

      arguments:
      * name -- name of this rule pool
      * priority -- priority of this pool (lower is better)
      """
      super ( DependencyRulePool, self ).__init__()
      if initial_rules is None:
         self.rules = list()
      else:
         self.rules = list ( initial_rules )
      self._rule_add    = self.rules.append
      self.name         = name
      self.priority     = priority
      # filter out deptype flags like "mandatory"
      self.deptype_mask = deptype_mask & deptype.RESOLVE_ALL
      # the "rule weight" is the sum of the rules' priorities
      #  it's used to compare/sort dependency pools with
      #  the same priority (lesser weight is better)
      self.rule_weight  = 0
   # --- end of __init__ (...) ---

   def empty ( self ):
      """Returns True if this pool has no rules."""
      return len ( self.rules ) == 0
   # --- end of empty (...) ---

   def sort ( self ):
      """Sorts this rule pool and determines its weight which is used
      to compare rule pools.
      """

      self.rules.sort ( key=lambda rule : rule.priority )

      rule_priority_sum = 0
      for r in self.rules: rule_priority_sum += r.priority
      self.rule_weight = rule_priority_sum

      return None
   # --- end of sort (...) ---

   def accepts ( self, deptype_mask, try_other=False ):
      """Returns True if this pool accepts the given deptype_mask."""
      return bool ( self.deptype_mask & deptype_mask )
   # --- end of accepts (...) ---

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

   def matches ( self, dep_env, skip_matches=0 ):
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

      elif skip_matches == 0:
         for rule in self.rules:
            result = rule.matches ( dep_env )
            if result:
               return result
      else:
         skipped = 0
         # python3 requires list ( range ... )
         order = list ( range ( len ( self.rules ) ) )

         if skip_matches < 0:
            skip_matches *= -1
            order.reverse()

         for index in order:
            result = self.rules [index].matches ( dep_env )
            if result:
               if skipped < skip_matches:
                  skipped += 1
               else:
                  return result

      # default return
      return None
   # --- end of matches (...) ---

   def export_rules ( self ):
      """Exports all rules. Typically, this generates text lines."""
      for rule in self.rules:
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
# --- end of DependencyRulePool ---
