# R overlay -- roverlay package, dictwalk
# -*- coding: utf-8 -*-
# Copyright (C) 2013 André Erdmann <dywi@mailerd.de>
# Distributed under the terms of the GNU General Public License;
# either version 2 of the License, or (at your option) any later version.

import roverlay.util.namespace
import roverlay.util.objects


def dictwalk_create_parent_v ( root, path, dict_create=None, cautious=True ):
   """Creates a dict tree structure using keys the given path. The last path
   element will not be created.

   Returns a 3-tuple
      ( <parent of the last path element>,
         <last path element>, <last path element exists>,
      )

   arguments:
   * root        -- dict root
   * path        -- path (list of keys)
   * dict_create -- constructor for dicts
   * cautious    -- do not create (dict) nodes if an element already exists
                    at a position. Defaults to True, which typically raises
                    a KeyError/TypeError if such an issue is (not) detected.
                    **NOT IMPLEMENTED**, always using cautious behavior
   """
   dcreate    = type ( root ) if dict_create is None else dict_create
   last_index = len ( path ) - 1
   pos        = root
   next_pos   = None

   for index, key in enumerate ( path ):
      if index == last_index:
         return ( pos, key, key in pos )
      elif key not in pos:
         next_pos  = dcreate()
         pos [key] = next_pos
         pos       = next_pos
         next_pos  = None
      else:
         pos       = pos [key]
   # -- end for

   raise Exception ( "unreachable code." )
# --- end of dictwalk_create_parent_v (...) ---

def dictwalk_create_element_v (
   root, path, constructor, overwrite=False, **kw
):
   parent, key, have_key = dictwalk_create_parent_v ( root, path, **kw )
   if have_key and not overwrite:
      return parent[key]
   else:
      new_elem = constructor()
      parent[key] = new_elem
      return new_elem
# --- end of dictwalk_create_element_v (...) ---

def dictwalk_create_parent ( root, *path ):
   return dictwalk_create_parent_v ( root, path )
# --- end of dictwalk_create_parent (...) ---

class DictWalker ( roverlay.util.namespace.Namespaceable ):

   DEFAULT_CONTAINER_TYPE = list

   def __init__ ( self, *args, **kwargs ):
      super ( DictWalker, self ).__init__()
      self.container_type = kwargs.get (
         'container_type', self.__class__.DEFAULT_CONTAINER_TYPE
      )

      self.add_value = (
         self._append_value if hasattr ( self.container_type, 'append' )
         else self._add_value
      )
   # --- end of __init__ (...) ---

   @roverlay.util.objects.abstractmethod
   def get_root ( self, *args, **kwargs ):
      pass
   # --- end of get_root (...) ---

   @roverlay.util.objects.abstractmethod
   def get_keypath ( self, *args, **kwargs ):
      pass
   # --- end of get_keypath (...) ---

   @roverlay.util.objects.abstractmethod
   def store_value ( self, value, *args, **kwargs ):
      pass
   # --- end of store_value (...) ---

   @roverlay.util.objects.abstractmethod
   def get_value_container ( self, *args, **kwargs ):
      pass
   # --- end of get_value_container (...) ---

   def _add_value ( self, value, *args, **kwargs ):
      self.get_value_container ( *args, **kwargs ).add ( value )
   # --- end of _add_value (...) ---

   def _append_value ( self, value, *args, **kwargs ):
      self.get_value_container ( *args, **kwargs ).append ( value )
   # --- end of _append_value (...) ---

# --- end of DictWalker ---


class FixedKeyDictWalker ( DictWalker ):

   def __init__ ( self, keypath, *args, **kwargs ):
      super ( FixedKeyDictWalker, self ).__init__ ( *args, **kwargs )

      if isinstance ( keypath, str ) or not hasattr ( keypath, '__iter__' ):
         self.keypath = ( keypath, )
      else:
         self.keypath = keypath
   # --- end of __init__ (...) ---

   #get_root() has to be implemented by derived classes

   def get_keypath ( self ):
      return self.keypath
   # --- end of get_keypath (...) ---

   def store_value ( self, value, *args, **kwargs ):
      parent, key, have_key = dictwalk_create_parent_v (
         self.get_root ( *args, **kwargs ), self.keypath
      )
      ret         = parent[key] if have_key else None
      parent[key] = value
      return ret
   # --- end of store_value (...) ---

   def get_value_container ( self, *args, **kwargs ):
      return dictwalk_create_element_v (
         self.get_root ( *args, **kwargs ), self.keypath, self.container_type,
         overwrite=False
      )
   # --- end of get_value_container (...) ---

# --- end of FixedKeyDictWalker ---
