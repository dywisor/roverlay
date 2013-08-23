# R overlay -- generic namespace
# -*- coding: utf-8 -*-
# Copyright (C) 2013 André Erdmann <dywi@mailerd.de>
# Distributed under the terms of the GNU General Public License;
# either version 2 of the License, or (at your option) any later version.

#import weakref

import roverlay.util.common
import roverlay.util.objects

DEBUG_GET_OBJECT = False


if DEBUG_GET_OBJECT:
   def debug_get_object ( msg, cls, args, kwargs ):
      print (
         "[ObjectNamespace] {:<17} :: {}, {}, {}".format (
            msg, cls, args, kwargs
         )
      )
   # --- end of debug_get_object (...) ---
# -- end if


class Namespaceable ( object ):
   @classmethod
   def from_namespace ( cls, namespace, *args, **kwargs ):
      return namespace.get_object_v ( cls, args, kwargs )
   # --- end of from_namespace (...) ---

   def __init__ ( self, *args, **kwargs ):
      super ( Namespaceable, self ).__init__()
   # --- end of __init__ (...) ---

# --- end of Namespaceable ---

class AbstractNamespace ( object ):

   def __init__ ( self, *args, **kwargs ):
      super ( AbstractNamespace, self ).__init__()
   # --- end of __init__ (...) ---

   @roverlay.util.objects.abstractmethod
   def zap ( self, zap_object_db=False ):
      pass
   # --- end of zap (...) ---

   def get_dict_hash ( self, d ):
      # note that this doesn't handle "recursive" dicts
      return roverlay.util.common.get_dict_hash ( d )
   # --- end of get_dict_hash (...) ---

   @roverlay.util.objects.abstractmethod
   def get_object_v ( self, cls, args=(), kwargs={} ):
      """Returns the desired object.

      The object will be created if it does not already exist in the
      object db of this namespace.

      !!! The object has to be "shareable", i.e. it must not be modified
          after constructing it (unless such a side-effect is intentional).

      arguments:
      * cls      --
      * *args    --
      * **kwargs --
      """
      pass
   # --- end of get_object_v (...) ---

   def get_object ( self, cls, *args, **kwargs ):
      """Like get_object_v(), but accepts a variable number of args."""
      return self.get_object_v ( cls, args, kwargs )
   # --- end of get_object (...) ---

# --- end of AbstractNamespace ---


class NullNamespace ( AbstractNamespace ):

   def zap ( self, *args, **kwargs ):
      pass
   # --- end of zap (...) ---

   def get_object_v ( self, cls, args=(), kwargs={} ):
      return cls ( *args, **kwargs )
   # --- end of get_object_v (...) ---

# --- end of NullNamespace ---


class SimpleNamespace ( AbstractNamespace ):
   """A namespace that caches all created objects."""

   def zap ( self, zap_object_db=False ):
      if zap_object_db:
         self._objects.clear()
   # --- end of zap (...) ---

   def __init__ ( self ):
      super ( SimpleNamespace, self ).__init__()

      # object db
      #  dict (
      #     class => dict (
      #        tuple(hash(args),hash(kwargs)) => instance
      #     )
      #  )
      #
      self._objects = dict()
   # --- end of __init__ (...) ---

   def get_object_v ( self, cls, args=(), kwargs={} ):
      ident = (
         hash ( args ) if args else 0,
         self.get_dict_hash ( kwargs ) if kwargs else 0,
      )

      objects = self._objects.get ( cls, None )

      if objects is None:
         if DEBUG_GET_OBJECT:
            debug_get_object ( "miss/new cls, obj", cls, args, kwargs )

         c = cls ( *args, **kwargs )
         self._objects [cls] = { ident : c }

      else:
         c = objects.get ( ident, None )

         if c is None:
            if DEBUG_GET_OBJECT:
               debug_get_object ( "miss/new obj", cls, args, kwargs )

            c = cls ( *args, **kwargs )
            objects [ident] = c
         elif DEBUG_GET_OBJECT:
            debug_get_object ( "hit/exist", cls, args, kwargs )

      return c
   # --- end of get_object_v (...) ---

# --- end of SimpleNamespace ---
