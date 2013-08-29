# R overlay -- overlay package, overlay base object
# -*- coding: utf-8 -*-
# Copyright (C) 2013 André Erdmann <dywi@mailerd.de>
# Distributed under the terms of the GNU General Public License;
# either version 2 of the License, or (at your option) any later version.

import logging

import roverlay.util.objects

class OverlayObject ( roverlay.util.objects.ReferenceTree ):
   """Base object for overlay objects (Overlay, Category, PackageDir) that
   provides some basic functionality:

   * common data variables: name, logger, physical_location, parent_ref
   * self-referencing: get_ref() (cached unless CACHE_REF is set to False)
   * back-referencing: get_parent()/get_upper(), set_parent()
   """

   # by default, keep a (weak) reference to self:
   # (a) Overlay: multiple Category objects use this ref
   # (b) Category: ^ PackageDir ...
   # (c) PackageDir: ^ PackageInfo ...
   #
   CACHE_REF = True

   def __init__ ( self, name, logger, directory, parent ):
      """OverlayObject constructor. Sets up common variables.

      arguments:
      * name      -- name of the overlay/category/package dir/...
      * logger    -- parent logger. Passing None results in using the root
                     logger. The object's logger is then
                      <parent logger>.getChild ( <name> )
      * directory -- filesystem location of the object
      * parent    -- parent object (object that "owns" this object)
                     This would be None when initializing the overlay's root,
                     the overlay's root when creating a category and the
                     category when creating a package dir.
      """
      super ( OverlayObject, self ).__init__ ( parent )
      self.name   = name
      self.logger = (
         logger.getChild ( name ) if logger else logging.getLogger ( name )
      )
      self.physical_location = directory
   # --- end of __init__ (...) ---

# --- end of OverlayObject ---
