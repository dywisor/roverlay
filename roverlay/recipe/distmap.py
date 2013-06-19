# R overlay -- recipe, distmap
# -*- coding: utf-8 -*-
# Copyright (C) 2013 André Erdmann <dywi@mailerd.de>
# Distributed under the terms of the GNU General Public License;
# either version 2 of the License, or (at your option) any later version.

import os.path

import roverlay.config
import roverlay.db.distmap

__all__ = [ 'access', ]

def setup():
   """Creates the static distmap instance."""
   global DISTMAP

   distmap_file = (
      roverlay.config.get ( 'OVERLAY.DISTMAP.dbfile', None )
      or (
         roverlay.config.get_or_fail ( 'CACHEDIR.root' )
         + os.path.sep + "distmap.db"
      )
   )

   if distmap_file:
      DISTMAP = roverlay.db.distmap.get_distmap (
         distmap_file        = distmap_file,
         distmap_compression = roverlay.config.get (
            'OVERLAY.DISTMAP.compression', 'bz2'
         ),
         ignore_missing=True
      )
   else:
      DISTMAP = None

   return DISTMAP
# --- end of setup (...) ---

def access():
   """Returns the static distmap instance."""
   return DISTMAP
# --- end of access (...) ---
