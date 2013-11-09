# R overlay -- ebuild creation, USE_EXPAND alias map
# -*- coding: utf-8 -*-
# Copyright (C) 2013 André Erdmann <dywi@mailerd.de>
# Distributed under the terms of the GNU General Public License;
# either version 2 of the License, or (at your option) any later version.

import roverlay.util

__all__ = [ 'UseFlagAliasMap', 'UseFlagRenameMap', ]

class _UseFlagMapBase ( dict ):

   class AbstractMethod ( NotImplementedError ):
      pass

   class BadFile ( Exception ):
      pass

   def __init__ ( self, from_file=None ):
      super ( _UseFlagMapBase, self ).__init__()
      if from_file:
         self.read_file ( from_file )
   # --- end of __init__ (...) ---

   def add_entry ( self, flag, alias_list, **kw ):
      raise self.__class__.AbstractMethod()
   # --- end of add_entry (...) ---

   def get_alias_map ( self ):
      raise self.__class__.AbstractMethod()
   # --- end of get_alias_map (...) ---

   def get_rename_map ( self ):
      raise self.__class__.AbstractMethod()
   # --- end of get_rename_map (...) ---

   def __invert__ ( self ):
      raise self.__class__.AbstractMethod()
   # --- end of __invert__ (...) ---

   def read_file ( self, filepath ):
      with open ( filepath, 'rt' ) as FH:
         current_flag = None
         for line in FH.readlines():
            sline = line.strip()
            if not sline or sline [0] == '#':
               pass
            elif sline [0] != line [0]:
               # append to last flag
               alias = sline.split ( None )
               if alias:
                  self.add_entry ( current_flag, alias )
            else:
               next_flag, alias = roverlay.util.headtail (
                  sline.split ( None )
               )
               next_flag = next_flag.lower()
               if not next_flag or next_flag == '=':
                  raise self.__class__.BadFile()
               elif alias:
                  if alias [0] == '=':
                     self.add_entry ( next_flag, alias [1:] )
                  else:
                     self.add_entry ( next_flag, alias )
               # -- end if;
               current_flag = next_flag
            # -- end if;
         # -- end for;
   # --- end of read_file (...) ---

   def _iter_sorted ( self ):
      return sorted ( self.items(), key=lambda e: e[0] )
   # --- end of _iter_sorted (...) ---

   def get_export_str ( self ):
      raise self.__class__.AbstractMethod()
   # --- end of get_export_str (...) ---

# --- end of _UseFlagMapBase ---


# { new_name => [original_name...] }
class UseFlagAliasMap ( _UseFlagMapBase ):

   def add_entry ( self, flag, alias_list, not_a_list=False ):
      existing_entry = self.get ( flag, None )
      if existing_entry:
         if not_a_list:
            existing_entry.add ( alias_list )
         else:
            existing_entry.update ( alias_list )
      elif not_a_list:
         self [flag] = { alias_list, }
      else:
         self [flag] = set ( alias_list )
   # --- end of add_entry (...) ---

   def get_rename_map ( self ):
      c = UseFlagRenameMap()
      for flag, alias in self.items():
         c.add_entry ( flag, alias )
      return c
   # --- end of get_rename_map (...) ---

   def get_alias_map ( self ):
      return self
   # --- end of get_alias_map (...) ---

   def __invert__ ( self ):
      return self.get_rename_map()
   # --- end of __invert__ (...) ---

   def get_export_str ( self ):
      return '\n'.join (
         '{flag} : {alias}'.format ( flag=k, alias=' '.join ( sorted ( v ) ) )
         for k, v in self._iter_sorted()
      )
   # --- end of get_export_str (...) ---

# --- end of UseFlagMap ---


# { original_name => new_name }
class UseFlagRenameMap ( _UseFlagMapBase ):

   def add_entry ( self, flag, alias_list ):
      for alias in alias_list:
         #assert alias not in self
         self [alias] = flag
   # --- end of add_entry (...) ---

   def get_rename_map ( self ):
      return self
   # --- end of get_rename_map (...) ---

   def get_alias_map ( self ):
      c = UseFlagAliasMap()
      for alias, flag in self.items():
         c.add_entry ( flag, alias, not_a_list=True )
      return c
   # --- end of get_alias_map ( self )

   def __invert__ ( self ):
      return self.get_alias_map()
   # --- end of __invert__ (...) ---

   def get_export_str ( self ):
      return self.get_alias_map().get_export_str()
   # --- end of get_export_str (...) ---

# --- end of UseFlagRenameMap ---
