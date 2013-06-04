# R overlay -- package rule actions, specific classes for modifing pkg info
# -*- coding: utf-8 -*-
# Copyright (C) 2013 André Erdmann <dywi@mailerd.de>
# Distributed under the terms of the GNU General Public License;
# either version 2 of the License, or (at your option) any later version.

import os.path

import roverlay.packagerules.actions.info

# FIXME: rename module?

class SrcDestRenameAction (
   roverlay.packagerules.actions.info.InfoRenameOtherAction
):

   def __init__ ( self, key, regex, subst, priority=1000 ):
      super ( SrcDestRenameAction, self ).__init__ (
         key=key, src_key="package_filename",
         dest_key="src_uri_dest", regex=regex, subst=subst, priority=priority
      )
   # --- end of __init__ (...) ---

   def apply_action ( self, p_info ):
      # don't modify the ".tar.gz" file extension
      #  TODO: other f-exts will be replaced, this is not critical, because:
      #  * all R packages end with .tar.gz
      #  * fext is an empty str if orig_value does not end with .tar.gz,
      #     so combining fname and fext does not break anything
      #  => worst case is "more accurate regex required" (+overhead here)
      #
      fname, fext, DONT_CARE = p_info [self.src_key].partition ( ".tar.gz" )

      p_info.set_direct_unsafe ( self.dest_key, self.re_sub ( fname ) + fext )
   # --- end of apply_action (...) ---

# --- end of SrcDestRenameAction (...) ---
