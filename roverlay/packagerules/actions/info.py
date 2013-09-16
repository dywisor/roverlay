# R overlay -- package rule actions, modify package information
# -*- coding: utf-8 -*-
# Copyright (C) 2013 André Erdmann <dywi@mailerd.de>
# Distributed under the terms of the GNU General Public License;
# either version 2 of the License, or (at your option) any later version.

__all__ = [
   'InfoRenameAction', 'LazyInfoRenameAction', 'SuperLazyInfoRenameAction',
   'InfoSetToAction',
]

import re
import string

import roverlay.packagerules.actions.attach
import roverlay.packagerules.abstract.actions


class InfoManipulatingAction (
   roverlay.packagerules.abstract.actions.PackageRuleAction
):
   FORMATTER    = string.Formatter()
   DEFAULT_VARS = dict.fromkeys (
      {
         'repo_name', 'version', 'package_name', 'name',
         'package_filename',
      },
      "U"
   )

   def __init__ ( self, key, priority=None ):
      super ( InfoManipulatingAction, self ).__init__ (
         priority=( 1000 if priority is None else priority )
      )
      self.key = key
   # --- end of __init__ (...) ---

   @classmethod
   def try_format ( cls, text, kwargs=None ):
      try:
         cls.FORMATTER.vformat (
            text, (), ( cls.DEFAULT_VARS if kwargs is None else kwargs )
         )
      except ( IndexError, KeyError, AttributeError ):
         return False
      else:
         return True
   # --- end of try_format (...) ---

   @classmethod
   def needs_formatter ( cls, text ):
      for literal_text, field_name, format_spec, conversion in (
         cls.FORMATTER.parse ( text )
      ):
         return bool ( field_name is not None )
      return False
   # --- end of needs_formatter (...) ---

# --- end of InfoManipulatingAction ---


class InfoRenameAction ( InfoManipulatingAction ):
   """A rename action modifies a package's info using regular expressions."""

   def __init__ ( self, key, regex, subst, priority=None ):
      """Constructor for InfoRenameAction.

      arguments:
      * key      -- info key that should be modified
      * regex    -- regex for matching a part of the original value
                     (using re.search())
      * subst    -- replacement for the matched value part
      * priority --
      """
      super ( InfoRenameAction, self ).__init__ ( key=key, priority=priority )

      self.regex = (
         re.compile ( regex ) if isinstance ( regex, str ) else regex
      )
      self.subst = subst
   # --- end of __init__ (...) ---

   def re_sub ( self, value ):
      # count? flags?
      return self.regex.sub ( self.subst, value )
   # --- end of re_sub (...) ---

   def apply_action ( self, p_info ):
      """Sets
      p_info [<stored key>] = <original value modified by stored regex,subst>

      arguments:
      * p_info --
      """
      # this only works for keys known _before_ reading desc data
      p_info.set_direct_unsafe ( self.key, self.re_sub ( p_info [self.key] ) )
   # --- end of apply_action (...) ---

   def gen_str ( self, level ):
      # FIXME: that's not always correct!
      # (could be solved by storing the original regex delimiter)
      yield (
         level * self.INDENT + 'rename ' + self.key
         + ' s/' + self.regex.pattern + '/' + self.subst + '/' # + flags
      )
   # --- end of gen_str (...) ---

# --- end of InfoRenameAction ---


class InfoRenameOtherAction ( InfoRenameAction ):
   """Like InfoRenameAction,
   but uses a pair of keys for setting/retrieving the actual value.
   """
   DEST_KEY = None
   SRC_KEY  = None

   def apply_action ( self, p_info ):
      orig_value = p_info [self.SRC_KEY]
      p_info.set_direct_unsafe ( self.DEST_KEY, self.re_sub ( orig_value ) )
   # --- end of apply_action (...) ---

# --- end of InfoRenameOtherAction ---


class LazyInfoRenameAction (
   roverlay.packagerules.actions.attach.LazyAction
):
   """A lazy variant of InfoRenameAction."""
   def __init__ ( self, key, regex, subst, priority=None ):
      super ( LazyInfoRenameAction, self ).__init__ (
         InfoRenameAction (
            key=key, regex=regex, subst=subst, priority=False
         ),
         priority=priority
      )

      # or use self._action.key (but self.key should point to the same object)
      self.key = key
   # --- end of __init__ (...) ---

   def can_apply_action ( self, p_info ):
      return p_info.has_key ( self.key )
   # --- end of can_apply_action (...) ---

# --- end of LazyInfoRenameAction ---


class SuperLazyInfoRenameAction (
   roverlay.packagerules.actions.attach.SuperLazyAction
):
   """A super lazy variant of InfoRenameAction."""

   # alternatively use multi-inheritance in [Super]Lazy<modify type>InfoAction

   def __init__ ( self, key, regex, subst, priority=1000 ):
      super ( SuperLazyInfoRenameAction, self ).__init__ (
         InfoRenameAction (
            key=key, regex=regex, subst=subst, priority=False
         ),
         priority=priority
      )
      self.key = key
   # --- end of __init__ (...) ---

   def can_apply_action ( self, p_info ):
      return p_info.has_key ( self.key )
   # --- end of can_apply_action (...) ---

# --- end of SuperLazyInfoRenameAction ---


class InfoSetToAction ( InfoManipulatingAction ):
   """A set-to action simply sets a package's info."""

   def __init__ ( self, key, value, priority=None ):
      """Constructor for InfoSetToAction.

      arguments:
      * key      -- info key that should be modified
      * value    -- value that will be stored
      * priority --
      """
      super ( InfoSetToAction, self ).__init__ ( key=key, priority=priority )
      self.value = value

      # bind apply_action()
      if self.needs_formatter ( value ):
         self.apply_action = self.apply_variable_value
      else:
         self.apply_action = self.apply_fixed_value
   # --- end of __init__ (...) ---

   def apply_fixed_value ( self, p_info ):
      """Sets p_info [<stored key>] = <stored value>.

      arguments:
      * p_info --
      """
      p_info.set_direct_unsafe ( self.key, self.value )
   # --- end of apply_fixed_value (...) ---

   def apply_variable_value ( self, p_info ):
      """Sets p_info [<stored key>] = <stored value> ~ <p_info._info>.

      arguments:
      * p_info --
      """
      # direct info dict access
      value = self.FORMATTER.vformat ( self.value, (), p_info._info )
      p_info.set_direct_unsafe ( self.key, value )
   # --- end of apply_variable_value (...) ---

   def _selftest ( self ):
      return self.try_format ( self.value )
   # --- end of _selftest (...) ---

   def gen_str ( self, level ):
      yield ( level * self.INDENT + 'set ' + self.key + ' ' + self.value )
   # --- end of gen_str (...) ---

# --- end of InfoSetToAction ---

# no lazy variants of InfoSetToAction - it should always be applied directly
