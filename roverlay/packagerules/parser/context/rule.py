# R overlay -- package rule parser, rule context
# -*- coding: utf-8 -*-
# Copyright (C) 2013 André Erdmann <dywi@mailerd.de>
# Distributed under the terms of the GNU General Public License;
# either version 2 of the License, or (at your option) any later version.

import roverlay.packagerules.abstract.rules
from roverlay.packagerules.abstract.rules import \
   IgnorePackageRule, PackageRule, NestedPackageRule

import roverlay.packagerules.parser.context.action
import roverlay.packagerules.parser.context.base
import roverlay.packagerules.parser.context.match


class RuleContext (
   roverlay.packagerules.parser.context.base.NestableContext
):
   """Class for creating rules from text input (feed(<>)) plus using a few
   control flow functions (end_of_rule(), begin_match(), begin_action()).
   """

   # CONTEXT_
   #  Used to set/compare the current mode, i.e. how text input will be
   #  interpreted.
   # * CONTEXT_NONE         -- end of the main rule ("self") has been reached
   # * CONTEXT_MATCH        -- set if in a match-block
   # -> CONTEXT_MAIN_MATCH  -- set if in the main match-block
   # -> CONTEXT_SUB_MATCH   -- set if in a nested match-block
   # * CONTEXT_ACTION       -- set if in an action-block
   # -> CONTEXT_MAIN_ACTION -- set if in the main action-block
   # -> CONTEXT_SUB_ACTION  -- set if in a nested action-block
   #
   # * CONTEXT_MAIN -- set if in any main block
   # * CONTEXT_SUB  -- set if in any nested block
   #
   # (use bitwise operators to check against these values)
   #
   CONTEXT_NONE            = 0 # == only
   CONTEXT_MAIN_MATCH      = 1
   CONTEXT_MAIN_ACTION     = 2
   CONTEXT_MAIN_ALT_ACTION = 4
   CONTEXT_SUB_MATCH       = 8
   CONTEXT_SUB_ACTION      = 16
   # else-block is a non-propagating status
   #CONTEXT_SUB_ALT_ACTION

   CONTEXT_MATCH           = CONTEXT_MAIN_MATCH      | CONTEXT_SUB_MATCH
   CONTEXT_ACTION          = CONTEXT_MAIN_ACTION     | CONTEXT_SUB_ACTION
   CONTEXT_MAIN_ANY_ACTION = CONTEXT_MAIN_ALT_ACTION | CONTEXT_MAIN_ACTION
   CONTEXT_SUB             = CONTEXT_SUB_MATCH       | CONTEXT_SUB_ACTION

   CONTEXT_MAIN = (
      CONTEXT_MAIN_MATCH | CONTEXT_MAIN_ACTION | CONTEXT_MAIN_ALT_ACTION
   )


   # -- end of CONTEXT_ --

   def __init__ ( self, namespace, level=0, priority=-1, mode=None ):
      super ( RuleContext, self ).__init__ ( namespace, level )

      if mode is None:
         if level == 0:
            self.mode = self.CONTEXT_MAIN_ACTION
         else:
            raise Exception ( "mode has to be set if level is non-zero." )
      else:
         self.mode = mode

      self.context             = self.CONTEXT_MAIN_MATCH
      self.priority            = priority
      self._action_context     = (
         roverlay.packagerules.parser.context.action.RuleActionContext (
            self.namespace
         )
      )
      self._alt_action_context = (
         roverlay.packagerules.parser.context.action.RuleActionContext (
            self.namespace
         )
      )
      self._match_context      = (
         roverlay.packagerules.parser.context.match.RuleMatchContext (
            namespace = self.namespace,
            priority  = priority
         )
      )
   # --- end of __init__ (...) ---

   def begin_match ( self, lino ):
      """Create/begin a match-block of a nested rule.

      arguments:
      * lino -- line number

      Raises: InvalidContext,
               match-blocks are only allowed within an action-block
      """
      # nested rules are stored in self._nested (and not in
      # self._action_context where they syntactically belong to)

      if self.context & self.CONTEXT_SUB_ACTION:
         # a nested rule inside a nested one (depth > 1)
         # => redirect to nested
         self.get_nested().begin_match ( lino )
         self.context |= self.CONTEXT_SUB_MATCH

      elif self.context & self.CONTEXT_MAIN_ACTION:
         # a nested rule (with depth = 1)
         self._new_nested ( priority=lino, mode=self.CONTEXT_MAIN_ACTION )
         self.context |= self.CONTEXT_SUB_MATCH

      elif self.context & self.CONTEXT_MAIN_ALT_ACTION:
         # a new nested rule in the else block (with depth = 1)
         self._new_nested ( priority=lino, mode=self.CONTEXT_MAIN_ALT_ACTION )
         self.context |= self.CONTEXT_SUB_MATCH

      else:
         # illegal
         raise self.InvalidContext()
   # --- end of begin_match (...) ---

   def begin_action ( self, lino ):
      """Create/begin an action block of a rule (nested or "self").

      arguments:
      * lino -- line number

      Raises: InvalidContext,
               an action block has to be preceeded by a match block
      """
      if self.context & self.CONTEXT_SUB_MATCH:
         # action-block of a nested rule
         # => redirect to nested
         self.get_nested().begin_action ( lino )
         self.context &= ~self.CONTEXT_SUB_MATCH
         self.context |= self.CONTEXT_SUB_ACTION

      elif self.context & self.CONTEXT_MAIN_MATCH:
         # begin of the main action-block
         self.context &= ~self.CONTEXT_MAIN_MATCH
         self.context |= self.CONTEXT_MAIN_ACTION

      else:
         # illegal
         raise self.InvalidContext()
   # --- end of begin_action (...) ---

   def begin_alternative_action ( self, lino ):
      """Create/begin an else-action block of a rule (nested or "self").

      arguments:
      * lino -- line number

      Raises: InvalidContext,
               an else-action block has to be preceeded by an action block
      """
      if self.context & self.CONTEXT_SUB_ACTION:
         # else-action-block of a nested rule
         #  => redirect to nested
         #  no status change as else-blocks are handled non-recursively
         self.get_nested().begin_alternative_action ( lino )

      elif self.context & self.CONTEXT_MAIN_ACTION:
         # begin of the main else-action-block
         self.context &= ~self.CONTEXT_MAIN_ACTION
         self.context |= self.CONTEXT_MAIN_ALT_ACTION

      else:
         # illegal
         raise self.InvalidContext()
   # --- end of begin_alternative_action (...) ---

   def end_of_rule ( self, lino ):
      """Has to be called whenever an end-of-rule statement has been reached
      and ends a rule, either this one or a nested one (depending on the
      context).

      Returns True if this rule has been ended, else False (end of a nested
      rule).

      arguments:
      * lino -- line number

      Raises: InvalidContext,
               rules can only be closed if within an action-block
      """
      if self.context & self.CONTEXT_SUB_ACTION:
         if self.get_nested().end_of_rule ( lino ):
            # end of child rule (depth=1)
            self.context &= ~self.CONTEXT_SUB_ACTION

# no-op, since self.context is already CONTEXT_SUB_ACTION
#         else:
#            # end of a nested rule (depth>1)
#            self.context = self.CONTEXT_SUB_ACTION

         return False

      elif self.context & self.CONTEXT_MAIN_ANY_ACTION:
         # end of this rule
         #self.context = self.CONTEXT_NONE
         self.context &= ~self.CONTEXT_MAIN_ANY_ACTION
         if self.context != self.CONTEXT_NONE:
            raise AssertionError (
               "broken context bit mask {:d}!".format ( self.context )
            )
         return True

      else:
         raise self.InvalidContext()
   # --- end of end_of_rule (...) ---

   def feed ( self, _str, lino ):
      """Feed this rule with input (text).

      arguments:
      * _str --
      * lino -- line number

      Raises: InvalidContext if this rule does not accept input
              (if self.context is CONTEXT_NONE)
      """
      if self.context & self.CONTEXT_SUB:
         return self.get_nested().feed ( _str, lino )

      elif self.context & self.CONTEXT_MAIN_MATCH:
         return self._match_context.feed ( _str, lino )

      elif self.context & self.CONTEXT_MAIN_ACTION:
         return self._action_context.feed ( _str, lino )

      elif self.context & self.CONTEXT_MAIN_ALT_ACTION:
         return self._alt_action_context.feed ( _str, lino )

      else:
         raise self.InvalidContext()
   # --- end of feed (...) ---

   def create ( self ):
      """Rule 'compilation'.

       Combines all read match- and action-blocks as well as any nested rules
       into a PackageRule instance (IgnorePackageRule, PackageRule or
       NestedPackageRule, whatever fits) and returns the result.

      Raises:
      * Exception if the resulting rule is invalid,
        e.g. no actions/acceptors defined.
      * InvalidContext if end_of_rule has not been reached
      """
      if self.context != self.CONTEXT_NONE:
         raise self.InvalidContext ( "end_of_rule not reached." )
      # -- if;

      package_rule  = None
      actions       = self._action_context.create()
      alt_actions   = self._alt_action_context.create()
      acceptor      = self._match_context.create()
      ACTION_IGNORE = self.namespace.get_ignore_action()

      if not acceptor:
         raise Exception ( "empty match-block makes no sense." )

      elif actions is None and alt_actions is None:
         raise Exception ( "ignore-all rule makes no sense." )

      elif len ( self._nested ) > 0:
         # nested rule
         package_rule = NestedPackageRule ( priority=self.priority )
         for nested in self._nested:
            nested_rule = nested.create()
            if nested.mode == self.CONTEXT_MAIN_ACTION:
               package_rule.add_rule ( nested_rule )
            elif nested.mode == self.CONTEXT_MAIN_ALT_ACTION:
               package_rule.add_alternative_rule ( nested_rule )
            else:
               raise Exception ( "nested rule has invalid mode" )

         if actions is None:
            package_rule.add_action ( ACTION_IGNORE )
         else:
            for rule_action in actions:
               package_rule.add_action ( rule_action )

         if alt_actions is None:
            package_rule.add_alternative_action ( ACTION_IGNORE )
         else:
            for rule_action in alt_actions:
               package_rule.add_alternative_action ( rule_action )

      elif actions is None:
         if alt_actions:
            # ignore rule with else-action block
            package_rule = PackageRule ( priority=self.priority )
            package_rule.add_action ( ACTION_IGNORE )

            for rule_action in alt_actions:
               package_rule.add_alternative_action ( rule_action )
         else:
            # ignore rule
            package_rule = IgnorePackageRule ( priority=self.priority )

      elif alt_actions is None:
         # normal rule with else-ignore block
         package_rule = PackageRule ( priority=self.priority )
         package_rule.add_alternative_action ( ACTION_IGNORE )

         for rule_action in actions:
            package_rule.add_action ( rule_action )

      elif actions or alt_actions:
         # normal rule with action and/or else-action block
         package_rule = PackageRule ( priority=self.priority )

         for rule_action in actions:
            package_rule.add_action ( rule_action )

         for rule_action in alt_actions:
            package_rule.add_alternative_action ( rule_action )

      else:
         raise Exception ( "empty action-block makes no sense." )
      # -- if;

      package_rule.set_acceptor ( acceptor )

      return package_rule
   # --- end of create (...) ---

# --- end of RuleContext ---
