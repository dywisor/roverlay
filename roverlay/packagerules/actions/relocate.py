# R overlay -- package rule actions, specific classes for modifing pkg info
# -*- coding: utf-8 -*-
# Copyright (C) 2013 André Erdmann <dywi@mailerd.de>
# Distributed under the terms of the GNU General Public License;
# either version 2 of the License, or (at your option) any later version.

import roverlay.packagerules.actions.info

# FIXME: rename module?

class AliasedInfoSetToAction (
   roverlay.packagerules.actions.info.InfoSetToAction
):
   DEST_KEY = None

   def __init__ ( self, action_key, value, priority=None ):
      super ( AliasedInfoSetToAction, self ).__init__ (
         key=self.__class__.DEST_KEY, value=value, priority=priority
      )
      self.action_key = action_key
   # --- end of __init__ (...) ---

   def gen_str ( self, level ):
      yield (
         ( level * self.INDENT )
         + 'set ' + self.action_key + ' ' + self.value
      )
   # --- end of gen_str (...) ---

# --- end of AliasedInfoSetToAction ---


class SrcDestSetToAction ( AliasedInfoSetToAction ):
   DEST_KEY = 'src_uri_dest'
# --- end of SrcDestSetToAction ---

class SrcDestRenameAction (
   roverlay.packagerules.actions.info.InfoRenameOtherAction
):
   SRC_KEY  = 'package_filename'
   DEST_KEY = 'src_uri_dest'

   def apply_action ( self, p_info ):
      # don't modify the ".tar.gz" file extension
      #  TODO: other f-exts will be replaced, this is not critical, because:
      #  * all R packages end with .tar.gz
      #  * fext is an empty str if orig_value does not end with .tar.gz,
      #     so combining fname and fext does not break anything
      #  => worst case is "more accurate regex required" (+overhead here)
      #
      fname, fext, DONT_CARE = p_info [self.SRC_KEY].partition ( ".tar.gz" )

      p_info.set_direct_unsafe ( self.DEST_KEY, self.re_sub ( fname ) + fext )
   # --- end of apply_action (...) ---

# --- end of SrcDestRenameAction (...) ---

class CategoryRenameAction (
   roverlay.packagerules.actions.info.InfoRenameOtherAction
):
   SRC_KEY  = 'repo_name'
   DEST_KEY = 'category'
# --- end of CategoryRenameAction ---
