# R overlay -- overlay package, distroot/distdir, static access
# -*- coding: utf-8 -*-
# Copyright (C) 2013 André Erdmann <dywi@mailerd.de>
# Distributed under the terms of the GNU General Public License;
# either version 2 of the License, or (at your option) any later version.

__all__ = [ 'get_configured', 'get_distdir', ]

import threading


import roverlay.config
import roverlay.recipe.distmap
import roverlay.overlay.pkgdir.distroot.distroot

_distroot_instance = None
_instance_lock = threading.Lock()

def access():
   return _distroot_instance
# --- end of access (...) ---

def get_new_configured():
   """Returns a new distroot instance that uses config values."""
   distdir_strategy = roverlay.config.get_or_fail (
      'OVERLAY.DISTDIR.strategy'
   )
   if distdir_strategy [-1] == 'tmpdir':
      return roverlay.overlay.pkgdir.distroot.distroot.TemporaryDistroot()
   else:
      return roverlay.overlay.pkgdir.distroot.distroot.PersistentDistroot (
         root     = roverlay.config.get_or_fail ( 'OVERLAY.DISTDIR.root' ),
         # generally, the "flat" distroot/distdir layout is desired as it
         # can serve as package mirror directory, so default to True here
         flat     = roverlay.config.get ( 'OVERLAY.DISTDIR.flat', True ),
         strategy = distdir_strategy,
         distmap  = roverlay.recipe.distmap.access(),
         verify   = roverlay.config.get ( 'OVERLAY.DISTDIR.verify', False ),
      )
# --- end of get_new_configured (...) ---

def get_configured():
   """Returns a distroot instance that uses config values.

   arguments:
   * static -- returns the 'static' instance (and creates it if necessary)
   """
   global _distroot_instance

   if _distroot_instance is None:
      global _instance_lock
      with _instance_lock:
         if _distroot_instance is None:
            _distroot_instance = get_new_configured()

   return _distroot_instance
# --- end of get_configured (...) ---

def get_distdir ( ebuild_name ):
   return get_configured().get_distdir ( ebuild_name )
# --- end of get_distdir (...) ---
