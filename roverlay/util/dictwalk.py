# R overlay -- roverlay package, dictwalk
# -*- coding: utf-8 -*-
# Copyright (C) 2013-2015 André Erdmann <dywi@mailerd.de>
# Distributed under the terms of the GNU General Public License;
# either version 2 of the License, or (at your option) any later version.

import roverlay.util.namespace
import roverlay.util.objects

def accumulate_key_value_list_dict_inplace (
   dst_dict, iterable, keyfunc, valfunc
):
   """Transfers items from the given iterable into a dict of lists.
   Inplace operation, takes the dst dict as first arg.

     dict< keyfunc(item) => list<valfunc(item)> >

   Returns: dst_dict

   arguments:
   * dst_dict  -- dict for storing the key/list<value> items
   * iterable  -- input items
   * keyfunc   -- function that returns an input item's dict key
   * valfunc   -- function that returns an input item's value
   """
   for item in iterable:
      key = keyfunc ( item )
      val = valfunc ( item )

      try:
         entry = dst_dict [key]
      except KeyError:
         dst_dict [key] = [ val ]
      else:
         entry.append ( val )
   # -- end for

   return dst_dict
# --- end of accumulate_key_value_list_dict_inplace (...) ---

def accumulate_key_value_list_dict ( iterable, keyfunc, valfunc ):
   """Transfers items from the given iterable into a dict of lists.

   Returns: dict

   arguments:
   * iterable  -- input items
   * keyfunc   -- function that returns an input item's dict key
   * valfunc   -- function that returns an input item's value
   """
   return accumulate_key_value_list_dict_inplace (
      dict(), iterable, keyfunc, valfunc
   )
# --- end of accumulate_key_value_list_dict (...) ---

def accumulate_key_value_list_dict_from_pairs ( iterable ):
   """Transfers items from the given iterable containg key,value 2-tuples
   into a dict of lists.

   Returns: dict

   arguments:
   * iterable -- input 2-tuples
   """
   return accumulate_key_value_list_dict (
      iterable, lambda kv: kv[0], lambda kv: kv[1]
   )
# --- end of accumulate_key_value_list_dict_from_pairs (...) ---

def dictwalk_create_parent_v ( root, path, dict_create=None, cautious=True ):
   """Creates a dict tree structure using keys from the given path.
   The last path element will not be created.

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

def dictwalk_create_parent ( root, *path, **kw ):
   """varargs variant - see dictwalk_create_parent_v() for details.

   arguments:
   * root  --
   * *path --
   * **kw  --
   """
   return dictwalk_create_parent_v ( root, path, **kw )
# --- end of dictwalk_create_parent (...) ---

def dictwalk_create_element_v (
   root, path, constructor, overwrite=False, **kw
):
   """Creates an element in a dict tree data structure.
   Does or does not overwrite existing elements, depending on the ovewrite
   parameter.

   This is basically the same as
   dictwalk_create_parent_v ( root, path, **kw )
   + create element in parent

   Returns: element (not necessarily newly created)

   arguments:
   root        -- dict
   path        -- list of keys, path[-1] is the element's key
   constructor -- function that creates a new element
   overwrite   -- whether the element should be recreated if it already exists
   **kw        -- additional keyword arguments for dictwalk_create_element_v
   """
   parent, key, have_key = dictwalk_create_parent_v ( root, path, **kw )
   if have_key and not overwrite:
      return parent[key]
   else:
      new_elem = constructor()
      parent[key] = new_elem
      return new_elem
# --- end of dictwalk_create_element_v (...) ---

class DictWalker ( roverlay.util.namespace.Namespaceable ):
   """Iterator/Wrapper for dealing with dict tree structures.

   The basic idea is to have objects with simple dicts and operate on them
   via this class (more precisely, a class derived from this one).
   """


   """
   The container type must provide a append() or add() method.
   append() takes precedence.
   """
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
      """Returns the root of the dict tree structure.

      Depending on the implementation,
      this method may create a new dict tree and add it to an object.

      arguments:
      * *args, **kwargs -- (depends on actual implementation)
      """
      pass
   # --- end of get_root (...) ---

   @roverlay.util.objects.abstractmethod
   def get_value_container ( self, *args, **kwargs ):
      """Returns a value container - possibly creates a new oneif necessary.

      Returns: value container, usually of type <cls>.DEFAULT_CONTAINER_TYPE

      arguments:
      * *args, **kwargs -- (depends on the actual implementation)
      """
      pass
   # --- end of get_value_container (...) ---

   def _add_value ( self, value, *args, **kwargs ):
      """Adds an item to a value container by using its add() method.

      Do not use this method directly - use add().

      Returns: None (implicit)

      arguments:
      * value           --
      * *args, **kwargs -- args for get_value_container()
      """
      self.get_value_container ( *args, **kwargs ).add ( value )
   # --- end of _add_value (...) ---

   def _append_value ( self, value, *args, **kwargs ):
      """Adds an item to a value container by using its append() method.

      Do not use this method directly - use add().

      Returns: None (implicit)

      arguments:
      * value           --
      * *args, **kwargs -- args for get_value_container()
      """
      self.get_value_container ( *args, **kwargs ).append ( value )
   # --- end of _append_value (...) ---

# --- end of DictWalker ---


class FixedKeyDictWalker ( DictWalker ):
   """A DictWalker that operates on a single dict tree element."""

   def __init__ ( self, keypath, *args, **kwargs ):
      super ( FixedKeyDictWalker, self ).__init__ ( *args, **kwargs )

      if isinstance ( keypath, str ) or not hasattr ( keypath, '__iter__' ):
         self.keypath = ( keypath, )
      else:
         self.keypath = keypath
   # --- end of __init__ (...) ---

   #get_root() has to be implemented by derived classes

   def get_value_container ( self, *args, **kwargs ):
      return dictwalk_create_element_v (
         self.get_root ( *args, **kwargs ), self.keypath, self.container_type,
         overwrite=False
      )
   # --- end of get_value_container (...) ---

# --- end of FixedKeyDictWalker ---
