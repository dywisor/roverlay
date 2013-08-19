# R overlay -- package rules
# -*- coding: utf-8 -*-
# Copyright (C) 2013 André Erdmann <dywi@mailerd.de>
# Distributed under the terms of the GNU General Public License;
# either version 2 of the License, or (at your option) any later version.

__all__ = [ 'PackageRules', ]

import logging

import roverlay.config
import roverlay.util

import roverlay.packagerules.abstract.rules
import roverlay.packagerules.parser.text

import roverlay.packagerules.actions.trace

class PackageRules ( roverlay.packagerules.abstract.rules.NestedPackageRule ):
   """The top level rule.
   Matches all PackageInfo instances and applies any rule that matches.
   """

   @classmethod
   def get_configured ( cls ):
      """Returns a PackageRules instance that uses the configured rules
      (roverlay.config).

      arguments:
      * cls --

      This is a stub since package rule loading is not implemented.
      """
      rules = PackageRules()

      flist = roverlay.config.get ( 'package_rules.files', False )
      if flist:
         loader = rules.get_parser()
         roverlay.util.for_all_files ( flist, loader.load )

      rules.prepare()

      return rules
   # --- end of get_configured (...) ---

   def __init__ ( self ):
      super ( PackageRules, self ).__init__ ( priority=-1 )
      self.logger = logging.getLogger ( self.__class__.__name__ )
      self.is_toplevel = True
   # --- end of __init__ (...) ---

   def _gen_rules_str ( self, level ):
      if level == 0:
         last_rule_index = len ( self._rules ) - 1
         for index, rule in enumerate ( self._rules ):
            for s in rule.gen_str ( level ):
               yield s
            if index < last_rule_index:
               yield ""
      else:
         for rule in self._rules:
            for s in rule.gen_str ( level ):
               yield s
   # --- end of _gen_rules_str (...) ---

   def prepare ( self ):
      super ( PackageRules, self ).prepare()
      self.set_logger ( self.logger )
   # --- end of prepare (...) ---

   def get_parser ( self ):
      """Returns a RuleParser that reads package rules from text files
      and adds them to this PackageRules instance.

      Note that prepare() has to be called after loading rules.
      """
      return roverlay.packagerules.parser.text.RuleParser ( self.add_rule )
   # --- end of get_parser (...) ---

   def accepts ( self, p_info ):
      """Returns True (and therefore doesn't need to be called)."""
      return True
   # --- end of accepts (...) ---

   def apply_alternative_actions ( self, p_info ):
      raise Exception ( "toplevel rule does not contain else-block actions." )
   # --- end of apply_alternative_actions (...) ---

   def add_alternative_action ( self, action ):
      raise Exception ( "toplevel rule does not accept else-block actions." )
   # --- end of add_alternative_action (...) ---

   def add_trace_actions ( self ):
      """Adds MarkAsModified actions to this rule and all nested ones.

      Meant for testing the package rule system.
      """
      marker = roverlay.packagerules.actions.trace.MarkAsModifiedAction ( -1 )

      for rule in self._iter_all_rules ( with_self=False ):
         if rule.has_actions():
            #and hasattr ( rule, 'add_action' )
            rule.add_action ( marker )

         if rule.has_alternative_actions():
            #and hasattr ( rule, 'add_alternative_action' )
            rule.add_alternative_action ( marker )

      self.prepare()
   # --- end of add_trace_actions (...) ---

   def __str__ ( self ):
      """Exports all rules to text in rule file syntax.

      Note:
       Due to the "lenient" syntax, the output is not necessarily identical
       to what has been read with get_parser().
      """
      return '\n'.join (
         self._gen_rules_str ( level=0 )
      )
   # --- end of __str__ (...) ---

# --- end of PackageRules ---
