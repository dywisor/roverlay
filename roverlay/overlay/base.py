# R overlay -- overlay package, overlay base object
# -*- coding: utf-8 -*-
# Copyright (C) 2013 André Erdmann <dywi@mailerd.de>
# Distributed under the terms of the GNU General Public License;
# either version 2 of the License, or (at your option) any later version.

import logging

import roverlay.util.objects

class OverlayObject ( roverlay.util.objects.ReferenceTree ):

   # always keep a (weak) reference to self:
   # (a) Overlay: multiple Category objects use this ref
   # (b) Category: ^ PackageDir ...
   # (c) PackageDir: ^ PackageInfo ...
   #
   CACHE_REF = True

   def __init__ ( self, name, logger, directory, parent ):
      super ( OverlayObject, self ).__init__ ( parent )
      self.name   = name
      self.logger = (
         logger.getChild ( name ) if logger else logging.getLogger ( name )
      )
      self.physical_location = directory
   # --- end of __init__ (...) ---

   # inherited:
   #def get_parent
   #def get_upper
   #def get_ref

# --- end of OverlayObject ---
