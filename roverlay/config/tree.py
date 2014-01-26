# R overlay -- config package, tree
# -*- coding: utf-8 -*-
# Copyright (C) 2012-2014 André Erdmann <dywi@mailerd.de>
# Distributed under the terms of the GNU General Public License;
# either version 2 of the License, or (at your option) any later version.

"""
Implements a tree structure for config values.

This module defines the following classes:
* ConfigTree -- config tree structure

Variables:
* CONFIG_INJECTION_IS_BAD -- a bool that indicates whether config value
                             injection is considered as 'okay' or 'bad'

"""

__all__ = [ 'ConfigTree', ]

import logging

import roverlay.config.exceptions
from roverlay.config           import const
from roverlay.config.loader    import ConfigLoader
from roverlay.config.util      import get_config_path
from roverlay.config.entryutil import find_config_path

CONFIG_INJECTION_IS_BAD = True

class ConfigTree ( object ):
   # static access to the first created ConfigTree
   instance = None

   def __init__ ( self, import_const=True, register_static=None ):
      """Initializes an ConfigTree, which is a container for options/values.
      Values can be stored directly (such as the field_definitions) or
      in a tree-like { section -> subsection[s] -> option = value } structure.
      Config keys cannot contain dots because they're used as config path
      separator.

      arguments:
      * import_const -- whether to deepcopy constants into the config tree or
                        not. Copying allows faster lookups.
      * register_static -- if True: register new instance as static
                           if None: same as for True unless a static instance
                                    is already registered
                           else: do nothing
      """
      if register_static is True or (
         self.__class__.instance is None and register_static is None
      ):
         self.__class__.instance = self
         self.logger = logging.getLogger ( self.__class__.__name__ )
      else:
         self.logger = logging.getLogger (
            "{}({:d}".format ( self.__class__.__name__, id ( self ) )
         )

      self._config           = None
      self._const_imported   = False
      self._field_definition = None
      self._use_extend_map   = None

      self.reset ( import_const=import_const )
   # --- end of __init__ (...) ---

   def reset ( self, import_const=None ):
      if import_const is not None:
         self._const_imported = bool ( import_const )

      self._config  = const.clone() if self._const_imported else dict()
      self._field_definition = None
      self._use_extend_map   = None
   # --- end of reset (...) ---

   def get_loader ( self ):
      """Returns a ConfigLoader for this ConfigTree."""
      return ConfigLoader ( self )
   # --- end of get_loader (...) ---

   def merge_with ( self, _dict ):
      """Merges this ConfigTree with a dict _dict.

      arguments:
      * _dict --

      returns: None (implicit)
      """
      def merge_dict ( pos, dict_to_merge ):
         """Recursively merges pos with dict_to_merge.

         arguments:
         * dict_to_merge --

         returns: None (implicit)
         """
         # this uses references where possible (no copy.[deep]copy,..)
         for key, val in dict_to_merge.items():
            if not key in pos:
               pos [key] = val
            elif isinstance ( pos [key], dict ):
               merge_dict ( pos [key], val )
            else:
               pos [key] = val
      # --- end of merge_dict (...) ---


      # strategy = theirs
      # unsafe operation (empty values,...)
      if _dict and isinstance ( _dict, dict ):

         u = { k : v for ( k, v ) in _dict.items() if v or v == 0 }
         merge_dict ( self._config, u )

      elif not _dict:
         pass

      else:
         raise roverlay.config.exceptions.ConfigUsageError()

   # --- end of merge_with (...) ---

   def _findpath (
      self, path,
      root=None, create=False, value=None, forcepath=False, forceval=False
   ):
      """All-in-one method that searches for a config path.
      It is able to create the path if non-existent and to assign a
      value to it.

      arguments:
      * path      -- config path as path list ([a,b,c]) or as path str (a.b.c)
      * root      -- config root (dict expected).
                      Uses self._config if None (the default)
      * create    -- create path if nonexistent
      * value     -- assign value to the last path element
                      an empty dict will be created if this is None and
                      create is True
      * forcepath -- if set and True: do not 'normalize' path if path is a list
      * forceval  -- if set and True: accept None as value
      """
      if path is None:
         return root
      elif isinstance ( path, ( list, tuple ) ) and forcepath:
         pass
      else:
         path = get_config_path ( path )


      config_position = self._config if root is None else root

      if config_position is None: return None

      last = len ( path ) - 1

      for index, k in enumerate ( path ):
         if len (k) == 0:
            continue

         if index == last and ( forceval or not value is None ):
            # overwrite entry
            config_position [k] = value
         elif not k in config_position:
            if create:
                  config_position [k] = dict()
            else:
               return None

         config_position = config_position [k]

      return config_position

   # --- end of _findpath (...) ---

   def inject ( self, key, value, suppress_log=False, **kw_extra ):
      """This method offer direct write access to the ConfigTree. No checks
      will be performed, so make sure you know what you're doing.

      arguments:
      * key        -- config path of the entry to-be-created/overwritten
                      the whole path will be created, this operation does not
                      fail if a path component is missing
                      ('<root>.<new>.<entry> creates "root",
                      "new" and "entry" if required)
      * value      -- value to be assigned
      * **kw_extra -- extra keywords for _findpath, e.g. forceval=True

      returns: None (implicit)
      """
      if not suppress_log:
         msg = 'config injection: value %s will '\
            'be assigned to config key %s ...' % ( value, key )

         if CONFIG_INJECTION_IS_BAD:
            self.logger.warning ( msg )
         else:
            self.logger.debug ( msg )

      self._findpath ( key, create=True, value=value, **kw_extra )
   # --- end of inject (...) ---

   def get ( self, key, fallback_value=None, fail_if_unset=False ):
      """Searches for key in the ConfigTree and returns its value.
      Searches in const if ConfigTree does not contain the requested key and
      returns the fallback_value if key not found.

      arguments:
      * key --
      * fallback_value --
      * fail_if_unset  -- fail if key is neither in config nor const

      raises:
      * ConfigKeyError -- key does not exist and fail_if_unset is True
      """

      config_value = self._findpath ( key )

      if config_value is None:
         fallback = None if fail_if_unset else fallback_value
         if not self._const_imported:
            config_value = const.lookup ( key, fallback )
         else:
            config_value = fallback

         if config_value is None and fail_if_unset:
            raise roverlay.config.exceptions.ConfigKeyError ( key )

      return config_value

   # --- end of get (...) ---

   def get_or_fail ( self, key ):
      """Alias to self.get ( key, fail_if_unset=True )."""
      return self.get ( key, fail_if_unset=True )
   # --- end of get_or_fail ---

   def get_by_name ( self, option_name, *args, **kwargs ):
      """Searches for an option referenced by name (e.g. OVERLAY_DIR)
      and returns its value. See ConfigTree.get() for details.

      This is an inefficient operation meant for setup/query scripts.
      Use get() where possible.

      arguments:
      * option_name
      * *args, **kwargs -- passed to get()

      raises:
      * ConfigOptionNotFound    -- option_name is unknown or hidden
      * ConfigEntryMapException -- config entry is broken
      * ConfigKeyError          -- key does not exist and fail_if_unset is True
      """
      return self.get ( find_config_path ( option_name ), *args, **kwargs )
   # --- end of get_by_name (...) ---

   def get_by_name_or_fail ( self, option_name ):
      """Alias to self.get_by_name ( key, fail_if_unset=True )."""
      return self.get_by_name ( option_name, fail_if_unset=True )
   # --- end of get_by_name_or_fail (...) ---

   def query_by_name ( self,
      request, empty_missing=False, convert_value=None
   ):
      """Creates a dict<var_name,value> of config options, referenced by name

      Returns: 2-tuple ( # of missing options, var dict ).

      arguments:
      * request       -- an iterable containing strings
                         or 2-tuples(option_name,var_name)
      * empty_missing -- whether to create empty entries for missing options
                         or not. Defaults to False.
      * convert_value -- if set and not None: convert config values using
                         this function before adding them to the resulting
                         dict
      """
      num_missing = 0
      retvars     = dict()

      for k in request:
         if (
            not isinstance ( k, str ) and hasattr ( k, '__iter__' )
            and len ( k ) > 1
         ):

            option_name = k[0]
            var_name    = k[1]
         else:
            option_name = str(k)
            var_name    = option_name
         # -- end if <set option_name/var_name>

         try:
            value = self.get_by_name_or_fail ( option_name )
         except (
            roverlay.config.exceptions.ConfigOptionNotFound,
            roverlay.config.exceptions.ConfigKeyError
         ):
            num_missing += 1
            if empty_missing:
               retvars [var_name] = ""
         else:
            if convert_value is not None:
               retvars [var_name] = convert_value ( value )
            else:
               retvars [var_name] = value
      # -- end for <request>

      return ( num_missing, retvars )
   # --- end of query_by_name (...) ---

   def get_field_definition ( self, force_update=False ):
      """Gets the field definition stored in this ConfigTree.

      arguments:
      * force_update -- enforces recreation of the field definition data.
      """
      if force_update:
         return self._field_definition.update()
      else:
         return self._field_definition
   # --- end of get_field_definition (...) ---

   def get_use_expand_map ( self ):
      """Returns the USE_EXPAND rename map stored in this ConfigTree."""
      return self._use_extend_map
   # --- end of get_use_expand_map (...) ---

   def _tree_to_str ( self, root, name, level=0 ):
      """Returns string representation of a config tree rooted at root.
      Uses recursion (DFS).

      arguments:
      * root  -- config 'root', is a value (config 'leaf') or a dict ('tree')
      * name  --
      * level --

      returns: string representation of the given root
      """

      indent = level * ' '
      var_indent =  indent + '* '
      if root is None:
         return "{}{} is unset\n".format ( var_indent, name )
      elif isinstance ( root, dict ):
         if len ( root ) == 0:
            return "{}{} is empty\n".format ( var_indent, name )
         else:
            extra = ''.join ( [
               self._tree_to_str ( n, r, level+1 ) for r, n in sorted (
                  root.items(),
                  key=lambda e: ( isinstance ( e[1], dict ), e[0] )
               )
            ] )
            return "{i}{n} {{\n{e}{i}}}\n".format ( n=name, e=extra, i=indent )
#      elif level == 1:
#         # non-nested config entry
#         return "\n{}{} = {!r}\n".format ( var_indent, name, root )
      else:
         return "{}{} = {!r}\n".format ( var_indent, name, root )
   # --- end of _tree_to_str (...) ---

   def visualize ( self, into=None ):
      """Visualizes the ConfigTree,
      either into a file-like object or as return value.

      arguments:
      * into -- if not None: write into file

      returns: string if into is None, else None (implicit)
      """
      _vis = self._tree_to_str ( self._config, 'ConfigTree', level=0 )
      if into is None:
         return _vis
      else:
         into.write ( _vis )
   # --- end of visualize (...) ---
