# R overlay -- dependency resolution, basic communcation module
# -*- coding: utf-8 -*-
# Copyright (C) 2012 André Erdmann <dywi@mailerd.de>
# Distributed under the terms of the GNU General Public License;
# either version 2 of the License, or (at your option) any later version.

"""basic communication methods to a dependency resolver

Provides two base classes that can be used for concrete communication classes:
* DependencyResolverListener -- an object that listens to the resolver.
                                It's not able to start communication with
                                the resolver, but useful to react on events
                                like 'dependency is unresolvable'.
* DependencyResolverChannel  -- an object that can interact with the resolver,
                                e.g. queue dependencies for resolution,
                                wait for results, parse them and send them
                                to the other end.
"""

__all__ = [ 'DependencyResolverChannel', 'DependencyResolverListener', ]

import threading
import sys

def channel_counter ():
   """A generator that yields (generator-wide) unique ids.
   Used to identify channels."""
   last_id = long ( -1 ) if sys.version_info < ( 3, ) else int ( -1 )

   while True:
      last_id += 1
      yield last_id


class DependencyResolverListener ( object ):
   """
   A DependencyResolverListener listens on events sent by the dep resolver.
   It has no access to the resolver, use DependencyResolverChannel for that.
   """

   def __init__ ( self ):
      """Initializes a DependencyResolverListener."""

      # the identifier must be unique and should not be changed after adding
      # the listener to the dep resolver
      # Using id (self) since listeners are expected to be closed when the
      # resolver closes.
      self.ident = id ( self )

      # the event mask is a bit vector used to determine whether
      # the listener accepts or ignores a specific notification
      self.event_mask = 0
   # --- end of __init__ (...) ---

   def accepts ( self, event_type ):
      """Returns whether this listener modules accepts the given event type.
      This can be used to prevent calculations if no module listens to the
      specific event.

      arguments:
      * event_type --
      """
      return bool ( self.event_mask & event_type )
   # --- end of accepts (...) ---

   def notify ( self, event_type, dep_env=None, pkg_env=None, **extra ):
      """Notify this listener about an event.

      arguments:
      * event_type --
      * dep_env    --
      * pkg_env    --
      * **extra    --
      """
      # stub only
      pass
   # --- end of notify (...) ---


class DependencyResolverChannel ( object ):
   """A DependencyResolverChannel can be used to communicate with the
   dependency resolver.

   class-wide variables:
   id_generator -- a generator that produces unique channels ids
   id_gen_lock  -- used to lock the generator
   """
   id_gen_lock  = threading.Lock()
   id_generator = channel_counter()

   def __init__ ( self, main_resolver ):
      """Initializes a DependencyResolverChannel which can be used to
      communicate with the dep resolver.

      arguments:
      * main_resolver -- dep resolver to connect to; setting this to None
                         results in automatic assignment when registering
                         with the first dep resolver.
      """
      #super ( DependencyResolverChannel, self ) . __init__ ()
      # channel identifiers must be unique even when the channel has been
      # deleted (id does not guarantee that)
      with DependencyResolverChannel.id_gen_lock:
         self.ident = next ( DependencyResolverChannel.id_generator )
      self._depres_master = main_resolver
   # --- end of __init__ (...) ---

   def set_resolver ( self, resolver, channel_queue=None, **extra ):
      """Assigns a resolver to this channel.

      arguments:
      * resolver      --
      * channel_queue -- ignored;
      * **extra       -- ignored
      """
      self._depres_master = resolver
   # --- end of set_resolver (...) ---

   def close ( self ):
      """Closes this channel."""
      self._depres_master.channel_closed ( self.ident )
      del self._depres_master
   # --- end of close (...) ---

   def enabled ( self ):
      """Returns True if this channel is enabled, else False."""
      return True
   # --- end of enabled (...) ---
