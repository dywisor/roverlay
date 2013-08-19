# R overlay -- abstract package rules, actions
# -*- coding: utf-8 -*-
# Copyright (C) 2013 André Erdmann <dywi@mailerd.de>
# Distributed under the terms of the GNU General Public License;
# either version 2 of the License, or (at your option) any later version.

__all__ = [ 'PackageRuleAction', ]

class PackageRuleAction ( object ):
   """PackageRuleActions manipulate PackageInfo instances."""

   class ActionNotValid ( Exception ):
      pass
   # --- end of RuleNotValid ---

   INDENT = 3 * ' '

   def __init__ ( self, priority=1000 ):
      super ( PackageRuleAction, self ).__init__()
      self.priority = priority
      self.logger   = None
   # --- end of __init__ (...) ---

   def set_logger ( self, logger ):
      self.logger = logger
   # --- end of set_logger (...) ---

   def apply_action ( self, p_info ):
      """Applies the action to the given PackageInfo.

      Returns False if the package should be filtered out.
      Any other value, especially None, should be interpreted as
      "successfully processed"
      (In constrast to the PackageRule.apply_actions(), where any false value
      means "package should be filtered out".)

      arguments:
      * p_info --
      """
      raise NotImplementedError()
   # --- end of apply_action (...) ---

   def _selftest ( self ):
      """Performs a self-test. See do_test() for details.

      Returns: success (True/False)

      Note: This method always returns True.
            Derived classes may implement it.
      """
      return True
   # --- end of _selftest (...) ---

   def do_test ( self, return_on_error=False ):
      """Tells this action to perform a self-test.

      arguments:
      * return_on_error -- return False if the self-test does not succeed

      Returns: True/False

      Raises: PackageRuleAction.ActionNotValid if the self-test fails and
              return_on_error does not evaluate to True.
      """
      result = self._selftest()
      if result or return_on_error:
         return result
      else:
         raise self.ActionNotValid ( '\"{action}\"'.format (
            action=( '\n'.join ( self.gen_str ( 0 ) ) )
         ) )
   # --- end of do_test (...) ---

   def gen_str ( self, level ):
      raise NotImplementedError (
         "{}.{}()".format ( self.__class__.__name__, "gen_str" )
      )
   # --- end of gen_str (...) ---

# --- end of PackageRuleAction ---
