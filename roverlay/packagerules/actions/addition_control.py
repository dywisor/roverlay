# R overlay -- package rule actions, addition-control actions
# -*- coding: utf-8 -*-
# Copyright (C) 2013 André Erdmann <dywi@mailerd.de>
# Distributed under the terms of the GNU General Public License;
# either version 2 of the License, or (at your option) any later version.

## names: PackageAdditionControl<type>Action


import roverlay.packagerules.abstract.actions

import roverlay.overlay.abccontrol

from roverlay.overlay.abccontrol import AdditionControlResult

ACTIONS = [
   'PackageAdditionControlDefaultAction',
   'PackageAdditionControlForceDenyAction',
   'PackageAdditionControlDenyReplaceAction',
   'PackageAdditionControlForceReplaceAction',
   'PackageAdditionControlReplaceOnlyAction',
   'PackageAdditionControlRevbumpOnCollisionAction',
]

__all__ = ACTIONS


class PackageAdditionControlActionBase (
   roverlay.packagerules.abstract.actions.PackageRuleAction
):
   KEYWORD         = "add-policy"
   CONTROL_KEYWORD = None
   CONTROL_RESULT  = None

   def apply_action ( self, p_info ):
      p_info.overlay_addition_override = (
         p_info.overlay_addition_override or 0
      ) | self.CONTROL_RESULT

      # more correct:
      # ao = (ao & CONTROL_RESULT_IMASK) | CONTROL_RESULT
      #   where CONTROL_RESULT_IMASK filters out all conflicting bits
   # --- end of apply_action (...) ---

   def gen_str ( self, level ):
      yield "{indent}{keyword} {control_keyword}".format (
         keyword         = self.KEYWORD,
         control_keyword = self.CONTROL_KEYWORD,
         indent          = ( level * self.INDENT )
      )
   # --- end of gen_str (...) ---

# --- end of PackageAdditionControlActionBase ---


class PackageAdditionControlDefaultAction (
   PackageAdditionControlActionBase
):
   CONTROL_KEYWORD = "default"
   CONTROL_RESULT  = AdditionControlResult.PKG_DEFAULT_BEHAVIOR


class PackageAdditionControlForceDenyAction (
   PackageAdditionControlActionBase
):
   CONTROL_KEYWORD = "force-deny"
   CONTROL_RESULT  = AdditionControlResult.PKG_FORCE_DENY


class PackageAdditionControlForceReplaceAction (
   PackageAdditionControlActionBase
):
   CONTROL_KEYWORD = "force-replace"
   CONTROL_RESULT  = AdditionControlResult.PKG_FORCE_REPLACE


class PackageAdditionControlDenyReplaceAction (
   PackageAdditionControlActionBase
):
   CONTROL_KEYWORD = "deny-replace"
   CONTROL_RESULT  = AdditionControlResult.PKG_DENY_REPLACE


class PackageAdditionControlRevbumpOnCollisionAction (
   PackageAdditionControlActionBase
):
   CONTROL_KEYWORD = "revbump-on-collision"
   CONTROL_RESULT  = AdditionControlResult.PKG_REVBUMP_ON_COLLISION


class PackageAdditionControlReplaceOnlyAction (
   PackageAdditionControlActionBase
):
   CONTROL_KEYWORD = "replace-only"
   CONTROL_RESULT  = AdditionControlResult.PKG_REPLACE_ONLY
