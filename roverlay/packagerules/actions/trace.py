# R overlay -- package rule actions, mark packages as modified
# -*- coding: utf-8 -*-
# Copyright (C) 2013 André Erdmann <dywi@mailerd.de>
# Distributed under the terms of the GNU General Public License;
# either version 2 of the License, or (at your option) any later version.

import roverlay.packagerules.abstract.actions

class TraceAction (
   roverlay.packagerules.abstract.actions.PackageRuleAction
):
   """Assigns a specific value (identifier) to the modified_by_package_rules
   variable of a PackageInfo object.
   """

   def __init__ ( self, trace_ident, priority=1000, _append=True ):
      super ( TraceAction, self ).__init__ ( priority=priority )
      self._ident  = trace_ident
      self._append = _append
   # --- end of __init__ (...) ---

   def apply_action ( self, p_info ):
      if self._append:
         if hasattr ( p_info, 'modified_by_package_rules' ):
            if (
               hasattr ( p_info.modified_by_package_rules, '__iter__' )
               and not isinstance ( p_info.modified_by_package_rules, str )
            ):
               p_info.modified_by_package_rules.append ( self._ident )
            else:
               p_info.modified_by_package_rules = [
                  p_info.modified_by_package_rules, self._ident
               ]
         else:
            p_info.modified_by_package_rules = [ self._ident ]
      else:
         p_info.modified_by_package_rules = self._ident
   # --- end of apply_action (...) ---

   def gen_str ( self, level ):
      yield ( level * self.INDENT ) + "trace " + str ( self._ident )
   # --- end of gen_str (...) ---


class MarkAsModifiedAction (
   roverlay.packagerules.abstract.actions.PackageRuleAction
):
   """Simply marks a PackageInfo object as modified."""

   def apply_action ( self, p_info ):
      """Marks a package as modified."""
      if (
         not hasattr ( p_info, 'modified_by_package_rules' )
         or not p_info.modified_by_package_rules
      ):
         p_info.modified_by_package_rules = True
   # --- end of apply_action (...) ---

   def gen_str ( self, level ):
      yield ( level * self.INDENT ) + "trace"
   # --- end of gen_str (...) ---
