# R overlay -- overlay package, addition control
# -*- coding: utf-8 -*-
# Copyright (C) 2014 André Erdmann <dywi@mailerd.de>
# Distributed under the terms of the GNU General Public License;
# either version 2 of the License, or (at your option) any later version.

"""overlay package, addition control"""

import roverlay.overlay.abccontrol
import roverlay.config


from roverlay.overlay.abccontrol import AdditionControlResult


class AdditionControl ( roverlay.overlay.abccontrol.AbstractAdditionControl ):

   @classmethod
   def get_configured ( cls, config=None ):
      if config is None:
         config = roverlay.config.access()

      ctrl_obj = cls()

      # ...

      return ctrl_obj

   def __init__ ( self ):
      raise NotImplementedError (
         "addition-control is done by package rules only, currently."
      )


   def check_package (
      self,
      category, package_dir, replacing_package, old_package
   ):
      return self.PKG_DEFAULT_BEHAVIOR
