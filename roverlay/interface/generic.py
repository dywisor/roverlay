# R overlay --
# -*- coding: utf-8 -*-
# Copyright (C) 2013 André Erdmann <dywi@mailerd.de>
# Distributed under the terms of the GNU General Public License;
# either version 2 of the License, or (at your option) any later version.

#import weakref

import roverlay.stats.collector

class RoverlayInterface ( object ):
   """Base class for roverlay interfaces.
   Provides functionality for attaching/detaching subinterfaces.
   """

   # stats collector
   STATS = roverlay.stats.collector.static

   def __init__ ( self ):
      """Initializes this interfaces."""
      super ( RoverlayInterface, self ).__init__()
      self._interfaces = dict()
   # --- end of __init__ (...) ---

   def close_interfaces ( self ):
      """Closes all subinterfaces."""
      if hasattr ( self, '_interfaces' ):
         for iface in self._interfaces.values():
            iface.close()
   # --- end of close_interfaces (...) ---

   def close ( self ):
      """Closes this interfaces and all of its subinterfaces.

      Returns: self
      """
      self.close_interfaces()
      return self
   # --- end of close (...) ---

   def update ( self ):
      """Updates this interface.

      Does nothing. Derived classes may implement it.

      Returns: self
      """
      return self
   # --- end of update (...) ---

   def attach_interface ( self, name, interface, close_detached=True ):
      """Adds a subinterface.

      arguments:
      * name           -- name of the interface
      * interface      -- interface object to add
      * close_detached -- if an interface with the same name has been replaced
                          by the new one: close it if True

      Returns: added interface
      """
      if name in self._interfaces:
         self.detach ( name, close=close_detached )

      self._interfaces [name] = interface
      return interface
   # --- end of attach_interface (...) ---

   def detach_interface ( self, name, close=False ):
      """Detaches an interface.

      arguments:
      * name  -- name of the interface
      * close -- close interface after detaching it

      Returns: detached interface if close is False, else True
      """
      detached = self._interfaces [name]
      del self._interfaces [name]
      if close:
         detached.close()
         return True
      else:
         return detached
   # --- end of detach_interface (...) ---

   def get_interface ( self, name ):
      """Provides access to a subinterface by name.

      arguments:
      * name -- name of the interface

      Returns: interface (object)

      Raises: KeyError if interface does not exist
      """
      return self._interfaces [name]
   # --- end of get_interface (...) ---

   def has_interface ( self, name ):
      """Returns True if a subinterface with the given name exists, else False.

      arguments:
      * name -- name of the interface
      """
      return name and name in self._interfaces
   # --- end of has_interface (...) ---

   def __getattr__ ( self, name ):
      """ Provides alternative access to subinterfaces via
      <self>.<subinterface name>_interface

      arguments:
      * name -- attribute name

      Returns: interface if name ends with '_interface'

      Raises: KeyError if name ends with '_interface' and the referenced
              interface does not exist
      """

      if name [-10:] == '_interface':
         iface_name = name [:-10]
         if iface_name and iface_name in self._interfaces:
            return self._interfaces [iface_name]

      raise AttributeError ( name )
   # --- end of __getattr__ (...) ---

# --- end of RoverlayInterface ---

class RoverlaySubInterface ( RoverlayInterface ):
   """Base class derived from RoverlayInterface for interfaces that have
   a parent interface.
   """

   def __init__ ( self, parent_interface ):
      """Initializes the subinterface. Creates references to shared objects
      like logger and config as well as a ref to the parent interface.

      arguments:
      * parent_interface --
      """
      super ( RoverlaySubInterface, self ).__init__()
      # weakref? (would require to explicitly keep "parent" instances around)
      self.parent    = parent_interface
      self.err_queue = parent_interface.err_queue
      self.config    = parent_interface.config
      self.logger    = parent_interface.logger
   # --- end of __init__ (...) ---
