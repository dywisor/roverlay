# R overlay -- package rule parser, base context
# -*- coding: utf-8 -*-
# Copyright (C) 2013 André Erdmann <dywi@mailerd.de>
# Distributed under the terms of the GNU General Public License;
# either version 2 of the License, or (at your option) any later version.

class BaseContext ( object ):

   class InvalidContext ( Exception ):
      pass
   # --- end of InvalidContext ---

   def __init__ ( self, namespace ):
      super ( BaseContext, self ).__init__()
      self.namespace = namespace
   # --- end of __init__ (...) ---

   def feed ( self, _str, lino ):
      raise NotImplementedError()
   # --- end of feed (...) ---

   def create ( self ):
      raise NotImplementedError()
   # --- end of create (...) ---

# --- end of BaseContext ---


class NestableContext ( BaseContext ):

   def __init__ ( self, namespace, level=0 ):
      super ( NestableContext, self ).__init__ ( namespace )
      self.level   = level
      self._nested = list()
   # --- end of __init__ (...) ---

   def _new_nested ( self, **kwargs ):
      o = self.__class__ (
         namespace = self.namespace,
         level     = self.level + 1,
         **kwargs
      )
      self._nested.append ( o )
      return o
   # --- end of _new_nested (...) ---

   def get_nested ( self ):
      return self._nested [-1]
   # --- end of get_nested (...) ---

# --- end of NestableContext ---
