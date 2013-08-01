# R overlay -- package rule actions, ignore package
# -*- coding: utf-8 -*-
# Copyright (C) 2013 André Erdmann <dywi@mailerd.de>
# Distributed under the terms of the GNU General Public License;
# either version 2 of the License, or (at your option) any later version.

import roverlay.packagerules.abstract.actions

__all__ = [ 'IgnoreAction', ]

class IgnoreAction (
   roverlay.packagerules.abstract.actions.PackageRuleAction
):

   KEYWORD = 'ignore'

   def apply_action ( self, p_info ):
      return False
   # --- end of apply_action (...) ---

   def gen_str ( self, level ):
      yield ( level * self.INDENT ) + self.KEYWORD
   # --- end of gen_str (...) ---

# --- end of IgnoreAction ---
