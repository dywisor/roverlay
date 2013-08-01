# R overlay -- package rule parser, parse text files
# -*- coding: utf-8 -*-
# Copyright (C) 2013 André Erdmann <dywi@mailerd.de>
# Distributed under the terms of the GNU General Public License;
# either version 2 of the License, or (at your option) any later version.

import roverlay.packagerules.parser.namespace
import roverlay.packagerules.parser.context.rule

class RuleParser ( object ):

   class NotParseable ( ValueError ):
      def __init__ ( self, line, lino ):
         super ( RuleParser.NotParseable, self ).__init__ (
            "in line {}: cannot parse '{}'.".format ( lino, line )
         )
      # --- end of __init__ (...) ---
   # --- end of NotParseable ---

   # control flow statements
   #  all other keywords are defined in the respective context classes,
   #  namely RuleContext, RuleMatchContext and RuleActionContext
   KEYWORDS_MATCH       = frozenset ({ 'match:', 'MATCH:', })
   KEYWORDS_ACTION      = frozenset ({ 'action:', 'ACTION:' })
   KEYWORDS_ACTION_ELSE = frozenset ({ 'else:', 'ELSE:' })
   KEYWORDS_END         = frozenset ({ 'end;', 'END;' })

   COMMENT_CHARS        = frozenset ({ '#', ';' })

   def _zap ( self ):
      self.namespace.zap ( zap_object_db=False )
      self._current_rule = None
      self._parsed_rules = list()
   # --- end of _zap (...) ---

   def __init__ ( self, add_rule_method ):
      """Constructor for RuleParser.

      arguments:
      * add_rule_method -- method that will be used to add created rules
      """
      super ( RuleParser, self ).__init__()
      self.namespace = roverlay.packagerules.parser.namespace.RuleNamespace()
      self.add_rule = add_rule_method
      self._zap()

      # the rule block (RuleContext) that is currently active
      self._current_rule = None
      # previous rule blocks
      self._parsed_rules = None
   # --- end of __init__ (...) ---

   def _feed ( self, l, lino ):
      """Feed this parser with text input.

      arguments:
      * l    -- stripped text line
      * lino -- line number
      """
      if len ( l ) > 0 and l[0] not in self.COMMENT_CHARS:
         if self._current_rule:
            if l in self.KEYWORDS_MATCH:
               self._current_rule.begin_match ( lino )
            elif l in self.KEYWORDS_ACTION:
               self._current_rule.begin_action ( lino )
            elif l in self.KEYWORDS_ACTION_ELSE:
               self._current_rule.begin_alternative_action ( lino )
            elif l in self.KEYWORDS_END:
               if self._current_rule.end_of_rule ( lino ):
                  # add rule to self._parsed_rules
                  self._parsed_rules.append ( self._current_rule )
                  self._current_rule = None
               # else end of a nested rule, do nothing
            else:
               self._current_rule.feed ( l, lino )

         elif l in self.KEYWORDS_MATCH:
            self._current_rule = (
               roverlay.packagerules.parser.context.rule.RuleContext (
                  self.namespace,
                  priority=lino
               )
            )

         else:
            raise self.NotParseable ( l, lino )
   # --- end of _feed (...) ---

   def _create ( self ):
      """Generator that yields package rules."""
      if self._current_rule:
         raise Exception ( "end_of_rule not reached." )

      for c in self._parsed_rules:
         yield c.create()
   # --- end of _create (...) --

   def load ( self, rule_file ):
      """Loads a rule file and adds the created rules using the add_rule
      method that has been given at initialization time (see __init__()).

      Returns: None (implicit)

      arguments:
      * rule_file --
      """
      self._zap()

      with open ( rule_file, 'r' ) as FH:
         for lino, line in enumerate ( FH.readlines() ):
            # ^lino := 0..(n-1), add +1
            self._feed ( line.strip(), lino + 1 )

      for rule in self._create():
         self.add_rule ( rule )
   # --- end of load (...) ---

# --- end of RuleParser ---
