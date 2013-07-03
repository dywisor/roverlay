# R overlay --
# -*- coding: utf-8 -*-
# Copyright (C) 2013 André Erdmann <dywi@mailerd.de>
# Distributed under the terms of the GNU General Public License;
# either version 2 of the License, or (at your option) any later version.

import roverlay

import roverlay.interface.root
import roverlay.interface.depres

roverlay.setup_initial_logger()

class MainInterface ( roverlay.interface.root.RootInterface ):

   def __init__ ( self, *args, **kwargs ):
      if args or kwargs:
         self.setup ( *args, **kwargs )
   # --- end of __init__ (...) ---

   def setup ( self, config_file, *args, **kw ):
      self.config_file = config_file
      super ( MainInterface, self ).__init__ (
         config_file=config_file, *args, **kw
      )
      self.__class__.register_interface (
         "depres", roverlay.interface.depres.DepresInterface
      )
      return True
   # --- end of setup (...) ---
