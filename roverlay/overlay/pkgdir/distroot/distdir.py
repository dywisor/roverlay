# R overlay -- overlay package, distdir
# -*- coding: utf-8 -*-
# Copyright (C) 2013 André Erdmann <dywi@mailerd.de>
# Distributed under the terms of the GNU General Public License;
# either version 2 of the License, or (at your option) any later version.

import os

__all__ = [ 'Distdir', 'PackageDistdir', ]

class Distdir ( object ):
   """A distroot view that provides distdir functionality."""

   # flat structure (one directory for all package files)

   def __str__ ( self ):
      return self.get_root()
   # --- end of __str__ (...) ---

   def __init__ ( self, distroot ):
      super ( Distdir, self ).__init__()
      self._distroot = distroot
   # --- end of __init__ (...) ---

   def add ( self, fpath, fname, p_info ):
      if self._distroot._add (
         fpath,
         self.get_root() + os.sep + ( fname or os.path.basename ( fpath ) )
      ):
         self._distroot.distmap_register ( p_info )
         return True
      else:
         return False
   # --- end of add (...) ---

   def get_root ( self ):
      return self._distroot.get_root()
   # --- end of get_root (...) ---

# --- end of Distdir ---


class PackageDistdir ( Distdir ):
   # per-package subdirs

   def __init__ ( self, distroot, package_name ):
      assert os.sep not in package_name

      super ( PackageDistdir, self ).__init__ ( distroot )
      self._root = self._distroot.get_root() + os.sep + package_name

      if not os.path.isdir ( self._root ):
         os.mkdir ( self._root, 0o755 )
   # --- end of __init__ (...) ---

   def get_root ( self ):
      return self._root
   # --- end of get_root (...) ---

# --- end of PackageDistdir ---
