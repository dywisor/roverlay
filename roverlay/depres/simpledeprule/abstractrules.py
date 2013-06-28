# R overlay -- simple dependency rules, abstract rules
# -*- coding: utf-8 -*-
# Copyright (C) 2012 André Erdmann <dywi@mailerd.de>
# Distributed under the terms of the GNU General Public License;
# either version 2 of the License, or (at your option) any later version.

"""implements abstract simple dependency rules"""

__all__ = [ 'FuzzySimpleRule', 'SimpleRule', ]

import logging

from roverlay import config
from roverlay.depres import deprule

TMP_LOGGER = logging.getLogger ('simpledeps')

class SimpleRule ( deprule.DependencyRule ):
   """A dependency rule that represents an ignored package in portage."""

   def __init__ ( self,
      dep_str=None, priority=50, resolving_package=None,
      is_selfdep=False, logger_name='simple_rule'
   ):
      """Initializes a SimpleIgnoreDependencyRule.

      arguments:
      * dep_str -- a dependency string that this rule is able to resolve
      * priority -- priority of this rule
      """
      super ( SimpleRule, self ) . __init__ ( priority )
      self.dep_alias = list()

      self.logger = TMP_LOGGER.getChild ( logger_name )

      self.is_selfdep = is_selfdep

      self.resolving_package = resolving_package

      self.prepare_lowercase_alias = True

      if not dep_str is None:
         self.dep_alias.append ( dep_str )

      if self.is_selfdep and dep_str is not None:
         # add the actual package name (replace '_' by '.') to self.dep_alias
         actual_name = dep_str.replace ( '_', '.' )
         if actual_name != dep_str:
            self.dep_alias.append ( dep_str )

   # --- end of __init__ (...) ---

   def done_reading ( self ):
      self.dep_alias = frozenset ( self.dep_alias )
      if self.prepare_lowercase_alias:
         self.dep_alias_low = frozenset ( x.lower() for x in self.dep_alias )

   def add_resolved ( self, dep_str ):
      """Adds an dependency string that should be matched by this rule.

      arguments:
      * dep_str --
      """
      self.dep_alias.append ( dep_str )
   # --- end of add_resolved (...) ---

   def _find ( self, dep_str, lowercase ):
      if lowercase:
         if hasattr ( self, 'dep_alias_low' ):
            if dep_str in self.dep_alias_low:
               return True

         elif dep_str in ( alias.lower() for alias in self.dep_alias ):
            return True

      return dep_str in self.dep_alias
   # --- end of _find (...) ---

   def matches ( self, dep_env, lowercase=True ):
      """Returns True if this rule matches the given DepEnv, else False.

      arguments:
      * dep_env --
      * lowercase -- if True: be case-insensitive when iterating over all
                     stored dep_strings
      """

      if self._find (
         dep_env.dep_str_low if lowercase else dep_env.dep_str, lowercase
      ):
         self.logger.debug (
            "matches {dep_str} with score {s} and priority {p}.".format (
               dep_str=dep_env.dep_str, s=self.max_score, p=self.priority
         ) )
         return ( self.max_score, self.resolving_package )

      return None
   # --- end of matches (...) ---

   def export_rule ( self ):
      """Generates text lines for this rule that can later be read using
      the SimpleDependencyRuleReader.
      """
      if self.resolving_package is None:
         resolving = ''
      else:
         resolving = self.resolving_package

         if self.is_selfdep:
            resolving = resolving.rpartition ( '/' ) [2]


      if hasattr ( self.__class__, 'RULE_PREFIX' ):
         resolving = self.__class__.RULE_PREFIX + resolving

      if self.is_selfdep:
         yield resolving

      elif len ( self.dep_alias ) == 0:
         pass

      elif len ( self.dep_alias ) == 1:
         yield "{} :: {}".format ( resolving, next ( iter ( self.dep_alias ) ) )

      else:
         yield resolving + ' {'
         for alias in self.dep_alias:
            yield "\t" + alias
         yield '}'

   def __str__ ( self ):
      return '\n'.join ( self.export_rule() )


class FuzzySimpleRule ( SimpleRule ):

   # 0 : version-relative, 1 : name only, 2 : std
   FUZZY_SCORE = ( 1250, 1000, 750 )
   max_score   = max ( FUZZY_SCORE )

   def __init__ ( self, *args, **kw ):
      super ( FuzzySimpleRule, self ).__init__ ( *args, **kw )
      self.prepare_lowercase_alias = True
   # --- end of __init__ (...) ---

   def match_prepare ( self, dep_env ):
      if self._find ( dep_env.dep_str_low, lowercase=True ):
         return ( 2, None )

      elif not hasattr ( dep_env, 'fuzzy' ):
         return None

      elif self.resolving_package is None:
         # ignore rule
         for fuzzy in dep_env.fuzzy:
            if self._find ( fuzzy ['name'], lowercase=True ):
               return ( 1, fuzzy )
      else:
         for fuzzy in dep_env.fuzzy:
            if self._find ( fuzzy ['name'], lowercase=True ):
               return ( 0, fuzzy )
            # -- end if find (=match found)
      # -- end if
      return None
   # --- end of match_prepare (...) ---

   def log_fuzzy_match ( self, dep_env, dep, score ):
      if dep is False:
         return None
      else:
         self.logger.debug (
            'fuzzy-match: {dep_str} resolved as '
            '{dep!r} with score={s}'.format (
               dep_str=dep_env.dep_str, dep=dep, s=score
            )
         )
         return ( score, dep )
   # --- end of log_fuzzy_match (...) ---

   def log_standard_match ( self, dep_env, score ):
      if dep is False:
         return None
      else:
         self.logger.debug (
            "matches {dep_str} with score {s} and priority {p}.".format (
               dep_str=dep_env.dep_str, s=score, p=self.priority
            )
         )
         return ( score, self.resolving_package )
   # --- end of log_standard_match (...) ---

   def handle_version_relative_match ( self, dep_env, fuzzy ):
      raise NotImplementedError()
   # --- end of handle_version_relative_match (...) ---

   def matches ( self, dep_env ):
      partial_result = self.match_prepare ( dep_env )
      if partial_result is None:
         return None
      else:
         match_type, fuzzy = partial_result
         score = self.FUZZY_SCORE [match_type]
         if match_type == 0:
            # real version-relative match
            return self.log_fuzzy_match (
               dep_env,
               self.handle_version_relative_match ( dep_env, fuzzy ),
               score
            )
         elif match_type == 1:
            # name-only match (ignore rule?)
            return self.log_fuzzy_match (
               dep_env, self.resolving_package, score
            )
         else:
            # non-fuzzy match
            return self.log_standard_match ( dep_env, score )
      # -- end if partial_result
   # --- end of matches (...) ---

# --- end of FuzzySimpleRule ---
