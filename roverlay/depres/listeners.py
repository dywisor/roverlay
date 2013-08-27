# R overlay -- dependency resolution, listener modules
# -*- coding: utf-8 -*-
# Copyright (C) 2012 André Erdmann <dywi@mailerd.de>
# Distributed under the terms of the GNU General Public License;
# either version 2 of the License, or (at your option) any later version.

"""dependency resolver listeners"""

__all__ = [
   'UnresolvableFileListener', 'UnresolvableSetFileListener',
   'ResolvedFileListener',
]

import threading
import os

from roverlay.depres               import events
from roverlay.depres.depenv        import DepEnv
from roverlay.depres.communication import DependencyResolverListener


def get_resolved_str ( dep_env ):
   return "{dep_str!r} as {dep!r}".format (
      dep_str=dep_env.dep_str, dep=dep_env.resolved_by.dep
   )
# --- end of get_resolved_str (...) ---

def get_unresolved_str ( dep_env ):
   return "0x{dep_type:x}, {dep_str}".format (
      dep_type=dep_env.deptype_mask, dep_str=dep_env.dep_str
   )
# --- end of get_unresolved_str (...) ---


class FileListener ( DependencyResolverListener ):
   """A dependency resolution listener that writes events to a file."""

   def __init__ ( self, _file, listen_mask ):
      """Initializes a FileListener.

      arguments:
      * _file       -- file to write
      * listen_mask -- a bit mask (int) that defines the events to be
                       processed.
     """
      super ( FileListener, self ) . __init__ ()

      self.fh         = None
      self.event_mask = listen_mask
      self._file      = _file

      if self._file is None:
         raise Exception ( "no file assigned" )
   # --- end of __init__ (...) ---

   def _event ( self, event_type, to_write ):
      """Writes to_write if event_type is accepted by self.event_mask."""
      if self.event_mask & event_type:
         if not self.fh:
            fdir = os.path.dirname ( self._file )
            if not os.path.isdir ( fdir ):
               os.makedirs ( fdir )
            self.fh = open ( self._file, 'a' )
         self.fh.write ( to_write + "\n" )
         # when to close? with open (...) as fh:...?
   # --- end of _event (...) ---

   def close ( self ):
      """Closes this listener (closes the file handle if open)."""
      if self.fh: self.fh.close()
   # --- end of close (...) ---


class SetFileListener ( DependencyResolverListener ):
   def __init__ ( self, _file, listen_mask ):
      super ( SetFileListener, self ) . __init__ ()

      self._buffer = set()

      self.event_mask  = listen_mask
      self._file       = _file

      if self._file is None:
         raise Exception ( "no file assigned" )
   # --- end of __init__ (...) ---

   def _event ( self, event_type, to_add ):
      if self.event_mask & event_type:
         self._buffer.add ( to_add )
   # --- end of _event (...) ---

   def write ( self, sort_entries=True ):
      try:
         fdir = os.path.dirname ( self._file )
         if not os.path.isdir ( fdir ):
            os.makedirs ( fdir )
         fh = open ( self._file, 'w' )

         if sort_entries:
            fh.write ( '\n'.join (
               sorted ( self._buffer, key=lambda x: x.lower() ) )
            )
         else:
            fh.write ( '\n'.join ( self._buffer ) )

         fh.write ( '\n' )

         fh.close()
      finally:
         if 'fh' in locals(): fh.close()
   # --- end of write (...) ---

   def close ( self ):
      self.write()
   # --- end of close (...) ---


class ResolvedFileListener ( FileListener ):
   """A FileListener that listens to 'dependency resolved' events."""

   def __init__ ( self, _file ):
      super ( ResolvedFileListener, self ) . __init__ (
         _file, events.DEPRES_EVENTS ['RESOLVED']
      )
   # --- end of __init__ (...) ---

   def notify ( self, event_type, dep_env=None, pkg_env=None, **extra ):
      self._event ( event_type, get_resolved_str ( dep_env ) )
   # --- end of notify (...) ---


class UnresolvableFileListener ( FileListener ):
   """A FileListener that listens to 'dependency unresolvable' events."""
   def __init__ ( self, _file ):
      super ( UnresolvableFileListener, self ) . __init__ (
         _file, events.DEPRES_EVENTS ['UNRESOLVABLE']
      )
   # --- end of __init__ (...) ---

   def notify ( self, event_type, dep_env=None, pkg_env=None, **extra ):
      self._event ( event_type, get_unresolved_str ( dep_env ) )
   # --- end of notify (...) ---


class UnresolvableSetFileListener ( SetFileListener ):
   """A SetFileListener that listens to 'dependency unresolvable' events."""

   def __init__ ( self, _file ):
      super ( UnresolvableSetFileListener, self ) . __init__ (
         _file, events.DEPRES_EVENTS ['UNRESOLVABLE']
      )
   # --- end of __init__ (...) ---

   def notify ( self, event_type, dep_env=None, pkg_env=None, **extra ):
      self._event ( event_type, get_unresolved_str ( dep_env ) )
   # --- end of notify (...) ---
