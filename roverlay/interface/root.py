# R overlay --
# -*- coding: utf-8 -*-
# Copyright (C) 2013 André Erdmann <dywi@mailerd.de>
# Distributed under the terms of the GNU General Public License;
# either version 2 of the License, or (at your option) any later version.

import logging

import roverlay
import roverlay.errorqueue

import roverlay.interface.generic

# does nothing if already initialized
roverlay.setup_initial_logger()

class RootInterface ( roverlay.interface.generic.RoverlayInterface ):

   SPAWN_MAP = dict()

   @classmethod
   def register_interface ( my_cls, name, cls, force=False ):
      if name and ( force or name not in my_cls.SPAWN_MAP ):
         my_cls.SPAWN_MAP [name] = cls
         return True
      else:
         return False
   # --- end of register_interface (...) ---

   def __init__ ( self,
      config_file=None, config=None, additional_config=None
   ):
      super ( RootInterface, self ).__init__()
      self.parent    = None
      self.err_queue = roverlay.errorqueue.ErrorQueue()

      if config is not None:
         self.config = config
      elif config_file is not None:
         self.config = roverlay.load_config_file (
            config_file, extraconf=additional_config
         )
      else:
         raise Exception ( "config, config_file?" )

      self.logger = logging.getLogger ( self.__class__.__name__ )
   # --- end of __init__ (...) ---

   def spawn_interface ( self, name ):
      if self.has_interface ( name ):
         return self.get_interface ( name )
      else:
         iface_cls = self.SPAWN_MAP.get ( name, None )
         if iface_cls is None:
            raise Exception (
               "unknown interface identifier {!r}".format ( name )
            )
         else:
            return self.attach_interface (
               name, iface_cls ( parent_interface=self )
            )
   # --- end of spawn_interface (...) ---
