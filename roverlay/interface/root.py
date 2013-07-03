# R overlay --
# -*- coding: utf-8 -*-
# Copyright (C) 2013 André Erdmann <dywi@mailerd.de>
# Distributed under the terms of the GNU General Public License;
# either version 2 of the License, or (at your option) any later version.

import logging

import roverlay
import roverlay.errorqueue
import roverlay.hook

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
      config_file=None, config=None, additional_config=None, is_installed=None
   ):
      super ( RootInterface, self ).__init__()
      self.parent    = None
      self.err_queue = roverlay.errorqueue.ErrorQueue()

      if getattr ( self, 'config', None ):
         pass
      elif config is not None:
         self.config = config
      elif config_file is not None:
         if additional_config is None:
            self.config = roverlay.load_config_file (
               config_file, extraconf={ 'installed': False, }
            )
         else:
            # modifies additional_config
            additional_config.update ( { 'installed': False, } )

            self.config = roverlay.load_config_file (
               config_file, extraconf=additional_config
            )
      else:
         raise Exception ( "config, config_file?" )


      if is_installed is not None:
         self.set_installed ( is_installed )
      elif self.config.get ( "installed", None ) is None:
         self.set_installed ( False )

      self.logger = logging.getLogger ( self.__class__.__name__ )

      roverlay.hook.setup()
   # --- end of __init__ (...) ---

   def set_installed ( self, status=True ):
      self.config.merge_with ( { 'installed': bool ( status ), } )
   # --- end of set_installed (...) ---

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

   def run_hook ( self, phase ):
      return roverlay.hook.run ( phase, catch_failure=False )
   # --- end of run_hook (...) ---
