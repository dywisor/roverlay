# R overlay -- package rule parser, namespace
# -*- coding: utf-8 -*-
# Copyright (C) 2013 André Erdmann <dywi@mailerd.de>
# Distributed under the terms of the GNU General Public License;
# either version 2 of the License, or (at your option) any later version.

import roverlay.util.namespace

import roverlay.packagerules.actions.ignore


class RuleNamespace ( roverlay.util.namespace.SimpleNamespace ):
   """a RuleNamespace manages RuleParser variables (e.g. objects)."""

   def __init__ ( self ):
      super ( RuleNamespace, self ).__init__()

      self._ignore_action = (
         roverlay.packagerules.actions.ignore.IgnoreAction()
      )
   # --- end of __init__ (...) ---

   def get_ignore_action ( self ):
      return self._ignore_action
   # --- end of get_ignore_action (...) ---

# --- end of RuleNamespace ---
