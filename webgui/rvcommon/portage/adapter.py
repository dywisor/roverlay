# R overlay -- common webgui functionality, roverlay<=>webgui adapter
# -*- coding: utf-8 -*-
# Copyright (C) 2014 André Erdmann <dywi@mailerd.de>
# Distributed under the terms of the GNU General Public License;
# either version 2 of the License, or (at your option) any later version.
from __future__ import absolute_import

from rvcommon import models

EXPORT_ADAPTERS = [ 'resolving_to_dep_atom', 'dep_atom_to_resolving' ]

__all__ = EXPORT_ADAPTERS


def resolving_to_dep_atom ( resolving_package ):
   """Converts a 'resolving package' str to a dependency atom model instance.

   Returns: DependencyAtom or FreeDependencyAtom or None

   arguments:
   * resolving_package -- str or None
   """
   parts = resolving_package.split ( None ) if resolving_package else None
   if not parts:
      return None

   numparts = len ( parts )

   # len(parts)==1 <=> resolving_package==parts[0]
   #  ==> resolving_package should be a valid dep atom
   if numparts == 1:
      return models.DependencyAtom.from_str ( parts[0] )

   # (a) non-empty str, maybe a compound dep "( catA/pkg1 catB/pkg2 )"
   elif numparts != 3:
      return models.FreeDependencyAtom.from_str ( resolving_package )

   elif parts[0] == '(' and parts[-1] == ')':
      assert parts[1]
      return models.DependencyAtom.from_str ( parts[1] )

   # (b) non-empty str
   else:
      return models.FreeDependencyAtom.from_str ( resolving_package )

# --- end of resolving_to_dep_atom (...) ---

def dep_atom_to_resolving ( dep_atom ):
   if not dep_atom:
      return None
   elif not isinstance ( dep_atom, models.DependencyAtomBase ):
      raise TypeError ( dep_atom )
   else:
      return dep_atom.get_dep_atom_str()
# --- end of dep_atom_to_resolving (...) ---
