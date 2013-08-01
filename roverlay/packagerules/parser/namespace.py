# R overlay -- package rule parser, namespace
# -*- coding: utf-8 -*-
# Copyright (C) 2013 André Erdmann <dywi@mailerd.de>
# Distributed under the terms of the GNU General Public License;
# either version 2 of the License, or (at your option) any later version.

import roverlay.util

import roverlay.packagerules.actions.ignore

DEBUG_GET_OBJECT = False

if DEBUG_GET_OBJECT:
   def debug_get_object ( msg, cls, args, kwargs ):
      print (
         "[ObjectNamespace] {:<17} :: {}, {}, {}".format (
            msg, cls, args, kwargs
         )
      )
   # --- end of debug_get_object (...) ---

class RuleNamespace ( object ):
   """a RuleNamespace manages RuleParser variables (e.g. objects)."""

   def zap ( self, zap_object_db=False ):
      if zap_object_db:
         self._objects.clear()
   # --- end of zap (...) ---

   def __init__ ( self ):
      super ( RuleNamespace, self ).__init__()

      # object db
      #  dict (
      #     class => dict (
      #        tuple(hash(args),hash(kwargs)) => instance
      #     )
      #  )
      #
      self._objects = dict()
      self._ignore_action = (
         roverlay.packagerules.actions.ignore.IgnoreAction()
      )
   # --- end of __init__ (...) ---

   def get_ignore_action ( self ):
      return self._ignore_action
   # --- end of get_ignore_action (...) ---

   def get_object ( self, cls, *args, **kwargs ):
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
      ident = (
         hash ( args) if args else 0,
         roverlay.util.get_dict_hash ( kwargs ) if kwargs else 0,
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
   # --- end of get_object (...) ---

# --- end of RuleNamespace ---
