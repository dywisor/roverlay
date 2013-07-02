# R overlay --
# -*- coding: utf-8 -*-
# Copyright (C) 2013 André Erdmann <dywi@mailerd.de>
# Distributed under the terms of the GNU General Public License;
# either version 2 of the License, or (at your option) any later version.

#import weakref

class RoverlayInterface ( object ):

   def __init__ ( self ):
      super ( RoverlayInterface, self ).__init__()
      self._interfaces = dict()
   # --- end of __init__ (...) ---

   def close_interfaces ( self ):
      if hasattr ( self, '_interfaces' ):
         for iface in self._interfaces.values():
            iface.close()
   # --- end of close_interfaces (...) ---

   def close ( self ):
      self.close_interfaces()
   # --- end of close (...) ---

   def update ( self ):
      pass
   # --- end of update (...) ---

   def attach_interface ( self, name, interface, close_detached=True ):
      if name in self._interfaces:
         self.detach ( name, close=close_detached )

      self._interfaces [name] = interface
      return interface
   # --- end of attach_interface (...) ---

   def detach_interface ( self, name, close=False ):
      detached = self._interfaces [name]
      if close:
         detached.close()
         return True
      else:
         return detached
   # --- end of detach_interface (...) ---

   def get_interface ( self, name ):
      return self._interfaces [name]
   # --- end of get_interface (...) ---

   def has_interface ( self, name ):
      return name and name in self._interfaces
   # --- end of has_interface (...) ---

   def __getattr__ ( self, name ):
      if name [-10:] == '_interface':
         iface_name = name [:-10]
         if iface_name and iface_name in self._interfaces:
            return self._interfaces [iface_name]

      raise AttributeError ( name )
   # --- end of __getattr__ (...) ---

# --- end of RoverlayInterface ---

class RoverlaySubInterface ( RoverlayInterface ):

   def __init__ ( self, parent_interface ):
      super ( RoverlaySubInterface, self ).__init__()
      # weakref? (would require to explicitly keep "parent" instances around)
      self.parent    = parent_interface
      self.err_queue = parent_interface.err_queue
      self.config    = parent_interface.config
      self.logger    = parent_interface.logger
   # --- end of __init__ (...) ---
