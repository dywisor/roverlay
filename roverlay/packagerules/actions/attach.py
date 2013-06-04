# R overlay -- package rule actions, "lazy" actions
# -*- coding: utf-8 -*-
# Copyright (C) 2013 André Erdmann <dywi@mailerd.de>
# Distributed under the terms of the GNU General Public License;
# either version 2 of the License, or (at your option) any later version.

__all__ = [ 'LazyAction', 'SuperLazyAction', ]


import roverlay.packagerules.abstract.actions


class LazyAction ( roverlay.packagerules.abstract.actions.PackageRuleAction ):
   """A lazy action simply adds an action to a PackageInfo object.
   The action can then be applied later on (initiated by the pkg info).

   Note that this cannot be used to filter out packages.
   """

   def __init__ ( self, actual_action, priority=1000 ):
      """Constructor for LazyAction.

      arguments:
      * actual_action -- object implementing at least apply_action(^1).
      * priority      --
      """
      super ( LazyAction, self ).__init__ ( priority=priority )
      self._action = actual_action
   # --- end of __init__ (...) ---

   def can_apply_action ( self, p_info ):
      """Returns True if the stored action can be applied to p_info,
      else False.
      """
      raise NotImplementedError ( "derived classes have to implement this." )
   # --- end of can_apply_action (...) ---

   def apply_action ( self, p_info ):
      """Attaches this action to p_info's lazy actions.

      arguments:
      * p_info
      """
      p_info.attach_lazy_action ( self )
   # --- end of apply_action (...) ---

   def try_apply_action ( self, p_info ):
      """Tries to apply the stored action.

      Returns True if the action could be applied (action condition evaluated
      to True), else False.

      Make sure to remove this action from p_info once it has been applied.

      arguments:
      * p_info --
      """
      if self.can_apply_action ( p_info ):
         if self._action.apply_action ( p_info ) is False:
            raise RuntimeError ( "lazy actions cannot filter out packages." )
         else:
            return True
      else:
         return False
   # --- end of try_apply_action (...) ---

   def gen_str ( self, level ):
      for s in self._action.gen_str ( level ): yield s
   # --- end of gen_str (...) ---

# --- end of LazyAction ---


class SuperLazyAction ( LazyAction ):
   """Like LazyAction, but tries to apply the action before attaching it.
   Useful if it's unknown whether an action can be applied a PackageInfo
   instance directly or not, costs one more check per package if it cannot
   be applied directly."""

   def apply_action ( self, p_info ):
      if not self.try_apply_action ( p_info ):
         p_info.attach_lazy_action ( self )
   # --- end of apply_action (...) ---

# --- end of SuperLazyAction ---
