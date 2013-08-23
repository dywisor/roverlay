# R overlay -- package rule actions, modify dependencies / depres
# -*- coding: utf-8 -*-
# Copyright (C) 2013 André Erdmann <dywi@mailerd.de>
# Distributed under the terms of the GNU General Public License;
# either version 2 of the License, or (at your option) any later version.

import roverlay.util.dictwalk
import roverlay.util.namespace
import roverlay.util.objects

import roverlay.depres.depresult

import roverlay.packagerules.abstract.actions



class DepConfAccess ( roverlay.util.dictwalk.FixedKeyDictWalker ):

   # ideally, use a data type that
   # (a) drops duplicates
   # (b) is ordered
   DEFAULT_CONTAINER_TYPE = set

   def __init__ ( self, keypath, virtual_key=None ):
      super ( DepConfAccess, self ).__init__ ( keypath )
      self.virtual_key = (
         self.keypath[-1] if virtual_key is None else virtual_key
      )
   # --- end of __init__ (...) ---

   def get_root ( self, p_info ):
      if p_info.depconf is None:
         p_info.depconf = dict()
      return p_info.depconf
   # --- end of get_root (...) ---

# --- end of DepConfAccess ---


class DependencyAction (
   roverlay.packagerules.abstract.actions.PackageRuleAction
):

   ACTION_KEYWORD = None

   @classmethod
   def from_namespace ( cls, namespace, keypath, *args, **kwargs ):
      depconf_access = namespace.get_object ( DepConfAccess, keypath )
      return namespace.get_object_v (
         cls, ( depconf_access, ) + args, kwargs
      )
   # --- end of from_namespace (...) ---

   def __init__ ( self, depconf_access, priority=1000 ):
      super ( DependencyAction, self ).__init__ ( priority=priority )
      self.depconf = depconf_access
   # --- end of __init__ (...) ---

   def get_action_keyword ( self ):
      return self.__class__.ACTION_KEYWORD
   # --- end of get_action_keyword (...) ---

   @roverlay.util.objects.abstractmethod
   def get_action_arg_str ( self ):
      pass
   # --- end of get_action_arg_str (...) ---

   def gen_str ( self, level ):
      yield (
         ( level * self.INDENT ) + self.get_action_keyword()
         + ' ' + str ( self.depconf.virtual_key )
         + ' \"' + self.get_action_arg_str() + '\"'
      )
   # --- end of gen_str (...) ---

# --- end of DependencyAction ---

class DependencyVarAction ( DependencyAction ):

   CATEGORY_KEY = None
   CONVERT_VALUE_TO_DEPRESULT = True

   @classmethod
   def from_namespace ( cls, namespace, deptype_key, value, *args, **kwargs ):
      assert cls.CATEGORY_KEY is not None

      depconf_access = namespace.get_object (
         DepConfAccess, ( cls.CATEGORY_KEY, deptype_key )
      )

      if cls.CONVERT_VALUE_TO_DEPRESULT:
         my_value = namespace.get_object_v (
            roverlay.depres.depresult.ConstantDepResult, ( value, 50, 0 )
         )
      else:
         my_value = value

      return namespace.get_object_v (
         cls, ( depconf_access, my_value ) + args, kwargs
      )
   # --- end of from_namespace (...) ---

#   @classmethod
#   def get_subclass (
#      cls, action_keyword, category_key, name=None, doc=None
#   ):
#      class NewDependencyVarAction ( cls ):
#         ACTION_KEYWORDS = action_keyword
#         CATEGORY_KEY    = category_key
#      # --- end of NewDependencyVarAction ---
#
#      if name is not None:
#         NewDependencyVarAction.__name__ = name
#      else:
#         NewDependencyVarAction.__name__ = 'New' + cls.__name__
#
#      if doc is not None:
#         NewDependencyVarAction.__doc__ = doc
#
#      return NewDependencyVarAction
#   # --- end of get_subclass (...) ---

   def __init__ ( self, depconf_access, value, priority=1000 ):
      super ( DependencyVarAction, self ).__init__ (
         depconf_access, priority=priority
      )
      self.value = value
   # --- end of __init__ (...) ---

   def get_action_arg_str ( self ):
      return str ( self.value )
   # --- end of get_action_arg_str (...) ---

   def apply_action ( self, p_info ):
      self.depconf.add_value ( self.value, p_info )
   # --- end of apply_action (...) ---

# --- end of DependencyVarAction ---

class DependencyInjectAction ( DependencyVarAction ):
   ACTION_KEYWORD = 'add'
   CATEGORY_KEY   = 'extra'
# --- end of DependencyInjectAction (...) ---
