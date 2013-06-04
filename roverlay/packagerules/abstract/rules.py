# R overlay -- abstract package rules, rules
# -*- coding: utf-8 -*-
# Copyright (C) 2013 André Erdmann <dywi@mailerd.de>
# Distributed under the terms of the GNU General Public License;
# either version 2 of the License, or (at your option) any later version.

import roverlay.util

__all__ = [ 'PackageRule', 'NestedPackageRule', 'IgnorePackageRule', ]


class IgnorePackageRule ( object ):
   """A rule that has only one action: filter packages."""

   def __init__ ( self, priority=100 ):
      super ( IgnorePackageRule, self ).__init__()
      self.priority   = priority
      self._acceptor  = None
      self.logger     = None
   # --- end of __init__ (...) ---

   def _iter_rules ( self, with_self=True ):
      if with_self:
         yield self
   # --- end of _iter_rules (...) ---

   def accepts ( self, p_info ):
      """Returns True if this rule matches the given PackageInfo else False.

      arguments:
      * p_info --
      """
      return self._acceptor.accepts ( p_info )
   # --- end of accepts (...) ---

   def set_acceptor ( self, acceptor ):
      """Assigns an acceptor to this rule.
      Such objects are used to match PackageInfo instances (in self.accepts()).

      arguments:
      * acceptor --
      """
      self._acceptor = acceptor
   # --- end of set_acceptor (...) ---

   def set_logger ( self, logger ):
      """Assigns a logger to this package rule.

      arguments:
      * logger --
      """
      self.logger = logger
      if hasattr ( self, '_acceptor' ):
         self._acceptor.set_logger ( self.logger )
   # --- end of set_logger (...) ---

   def apply_actions ( self, p_info ):
      """Ignores a PackageInfo by returning False.

      arguments:
      * p_info --
      """
      return False
   # --- end of apply_actions (...) ---

   def prepare ( self ):
      """
      Prepares this rule for usage. Has to be called after adding actions.
      """
      if hasattr ( self, '_acceptor' ):
         self._acceptor.prepare()
   # --- end of prepare (...) ---

   def _gen_action_str ( self, level ):
      yield level * '   ' + 'ignore'
   # --- end of _gen_action_str (...) ---

   def gen_str ( self, level ):
      indent = level * '   '

      yield ( indent + 'MATCH:' )
      for s in self._acceptor.gen_str ( level=( level + 1 ), match_level=0 ):
         yield s

      yield ( indent + 'ACTION:' )
      for s in self._gen_action_str ( level=( level + 1 ) ):
         yield s

      if hasattr ( self, '_gen_rules_str' ):
         for s in self._gen_rules_str ( level=( level + 1 ) ):
            yield s

      yield ( indent + 'END;' )
   # --- end of gen_str (...) ---

   def __str__ ( self ):
      return '\n'.join ( self.gen_str ( level=0 ) )
   # --- end of __str__ (...) ---

# --- end of IgnorePackageRule ---


class PackageRule ( IgnorePackageRule ):
   """A package rule is able to determine whether it matches
   a given PackageInfo instance (using Acceptor instances)
   and applies zero or more actions (using PackageAction instances) to the
   package info.
   """

   def __init__ ( self, priority=1000 ):
      super ( PackageRule, self ).__init__( priority )
      self._actions = list()
   # --- end of __init__ (...) ---

   def prepare ( self ):
      """
      Prepares this rule for usage. Has to be called after adding actions.
      """
      super ( PackageRule, self ).prepare()
      self._actions = roverlay.util.priosort ( self._actions )
   # --- end of prepare (...) ---

   def set_logger ( self, logger ):
      """Assigns a logger to this package rule and all actions.

      arguments:
      * logger --
      """
      super ( PackageRule, self ).set_logger ( logger )
      action_logger = self.logger.getChild ( 'Action' )
      for action in self._actions:
         action.set_logger ( action_logger )
   # --- end of set_logger (...) ---

   def apply_actions ( self, p_info ):
      """Applies all actions to the given PackageInfo.

      The return value indicates whether the package has been filtered out
      (do not process it any longer -> False) or not (True).

      arguments:
      * p_info -- PackageInfo object that will be modified
      """
      for action in self._actions:
         # "is False" - see ./actions.py
         if action.apply_action ( p_info ) is False:
            return False
      return True
   # --- end of apply_actions (...) ---

   def add_action ( self, action ):
      """Adds an action to this rule.

      arguments:
      * action --
      """
      self._actions.append ( action )
   # --- end of add_action (...) ---

   def _gen_action_str ( self, level ):
      for x in self._actions:
         for s in x.gen_str ( level=level ):
            yield s
   # --- end of _gen_action_str (...) ---

# --- end of PackageRule ---


class NestedPackageRule ( PackageRule ):
   """A rule that consists of zero or more subordinate rules."""

   def __init__ ( self, priority=2000 ):
      super ( NestedPackageRule, self ).__init__ ( priority )
      self._rules = list()
   # --- end of __init__ (...) ---

   def _gen_rules_str ( self, level ):
      for rule in self._rules:
         for s in rule.gen_str ( level ):
            yield s
   # --- end of _gen_rules_str (...) ---

   def _iter_rules ( self, with_self=True ):
      if with_self:
         yield self

      for rule in self._rules:
         for nested_rule in rule._iter_rules ( with_self=True ):
            yield nested_rule
   # --- end of _iter_rules (...) ---

   def set_logger ( self, logger ):
      """Assigns a logger to this package rule and all actions.

      arguments:
      * logger --
      """
      super ( NestedPackageRule, self ).set_logger ( logger )
      if hasattr ( self, 'is_toplevel' ) and self.is_toplevel:
         nested_logger = self.logger.getChild ( 'nested' )
         for nested_rule in self._rules:
            nested_rule.set_logger ( nested_logger )
      else:
         for nested_rule in self._rules:
            nested_rule.set_logger ( self.logger )
   # --- end of set_logger (...) ---

   def prepare ( self ):
      """
      Prepares this rule for usage. Has to be called after adding actions.
      """
      super ( NestedPackageRule, self ).prepare()
      for rule in self._rules:
         rule.prepare()
      self._rules = roverlay.util.priosort ( self._rules )
   # --- end of prepare (...) ---

   def apply_actions ( self, p_info ):
      """Applies all actions to the given PackageInfo.

      The return value indicates whether the package has been filtered out
      (do not process it any longer -> False) or not (True).

      arguments:
      * p_info -- PackageInfo object that will be modified
      """
      if super ( NestedPackageRule, self ).apply_actions ( p_info ):
         for rule in self._rules:
            if rule.accepts ( p_info ) and not rule.apply_actions ( p_info ):
               return False
         return True
      else:
         return False
   # --- end of apply_actions (...) ---

   def add_rule ( self, rule ):
      """Adds a rule.

      arguments:
      * rule --
      """
      self._rules.append ( rule )
   # --- end of add_rule (...) ---

# --- end of NestedPackageRule ---
