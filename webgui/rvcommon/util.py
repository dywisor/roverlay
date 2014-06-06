# R overlay -- common webgui functionality
# -*- coding: utf-8 -*-
# Copyright (C) 2014 André Erdmann <dywi@mailerd.de>
# Distributed under the terms of the GNU General Public License;
# either version 2 of the License, or (at your option) any later version.

from django.contrib import admin

import collections
import functools


def create_model ( cls, *args, **kwargs ):
   return cls.objects.create ( *args, **kwargs )
# --- end of create_model (...) ---

def get_or_create_model ( cls, *args, **kwargs ):
   return cls.objects.get_or_create ( *args, **kwargs ) [0]
# --- end of get_or_create_model (...) ---

def register_models ( module, names=None ):
   for name in ( module.EXPORT_MODELS if names is None else names ):
      admin.site.register ( getattr ( module, name ) )
# --- end of register_models (...) ---

def dedup_attr_lists ( attr_name, *modules ):
   result_set = set()

   for module in modules:
      try:
         attr = getattr ( module, attr_name )
      except AttributeError as err:
         err.args = (
            (
               '{module.__name__!r} module has no attribute '
               '{attr_name!r}'.format ( module=module, attr_name=attr_name )
            ),
         )

         raise
      else:
         result_set.update ( attr )

   return list(result_set)
# --- end of dedup_attr_lists (...) ---

def create_revmap ( vk_iter ):
   return { v: k for k, v in vk_iter }

def get_revmap ( x ):
   return create_revmap ( x.items() if hasattr ( x, 'items' ) else x )

def undictify ( iterable, t=tuple ):
   if iterable is None:
      return t()
   elif isinstance ( iterable, ( dict, collections.UserDict ) ):
      return t ( iterable.items() )
   elif isinstance ( iterable, t ):
      return iterable
   else:
      return t ( iterable )

def bitsum ( numbers ):
   return functools.reduce ( lambda a, b: a|b, numbers, 0 )

def bitsum_unique ( atoms ):
   bitsum = 0
   for atom in atoms:
      if bitsum & atom:
         raise ValueError ( "not unique" )
      bitsum |= atom
   return bitsum


def get_intmask_translator ( mapping, from_index, to_index ):
   """Creates a 'translator' function, which converts an integer mask
   from a model to its object equivalent (or vice versa).

   Returns: translator function

   arguments:
   * mapping    -- n-tuple of k-tuples <value_0, value_1, ..., value_k>
   * from_index -- translation source index (int 0..(k-1))
   * to_index   -- translation dest   index (int 0..(k-1))
   """
   def wrapped ( value ):
      s = 0
      for pair in mapping:
         if value & pair [from_index]:
            s |= pair [to_index]
      return s

   return wrapped
# --- end of get_intmask_translator (...) ---


class InterfaceProxy ( object ):
   """An interface that redirects requests for unknown attributes to another
   (back-end) interface.

   The overall goal is to keep the backing interface's vars/method intact,
   no matter what is implemented/set by the proxy class.
   """

   def __init__ ( self, interface ):
      super ( InterfaceProxy, self ).__init__()
      self.interface = interface
   # --- end of __init__ (...) ---

   def __getattr__ ( self, name ):
      if name == "interface":
         raise AttributeError ( name )

      attr = getattr ( self.interface, name )

      if hasattr ( attr, '__call__' ):
         # lazy-bind methods
         setattr ( self, name, attr )

      return attr
   # --- end of __getattr__ (...) ---

# --- end of InterfaceProxy ---
