# R overlay -- package rules, trivial acceptors
# -*- coding: utf-8 -*-
# Copyright (C) 2013 André Erdmann <dywi@mailerd.de>
# Distributed under the terms of the GNU General Public License;
# either version 2 of the License, or (at your option) any later version.

"""
This module provides so-called trivial acceptors.

An acceptor is trivial if (and only if) the return value of its accepts()
function does not depend on any arg (i.e. the PackageInfo instance).
In most cases the return value is known a priori.
(An exception would be a "RandomAcceptor" class.)
"""

import roverlay.packagerules.abstract.acceptors

class TrueAcceptor ( roverlay.packagerules.abstract.acceptors.Acceptor ):

   def accepts ( self, *a, **b ):
      return True
   # --- end of accepts (...) ---

   def gen_str ( self, level, match_level ):
      yield (
         self._get_gen_str_indent ( level, match_level )
         + 'any'
      )
   # --- end of gen_str (...) ---

# --- end of TrueAcceptor ---


class FalseAcceptor ( roverlay.packagerules.abstract.acceptors.Acceptor ):

   def accepts ( self, *a, **b ):
      return False
   # --- end of accepts (...) ---

   def gen_str ( self, level, match_level ):
      yield (
         self._get_gen_str_indent ( level, match_level )
         + 'none'
      )
   # --- end of gen_str (...) ---

# --- end of FalseAcceptor ---
