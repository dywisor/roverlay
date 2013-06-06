# R overlay -- overlay package, overlay additions dir
# -*- coding: utf-8 -*-
# Copyright (C) 2013 André Erdmann <dywi@mailerd.de>
# Distributed under the terms of the GNU General Public License;
# either version 2 of the License, or (at your option) any later version.

import os
import re

class AdditionsDir ( object ):

   def __init__ ( self, fspath, name=None, parent=None ):
      self.root   = str ( fspath ) if fspath else None
      self.parent = parent
      self.name   = name
   # --- end of __init__ (...) ---

   def exists ( self ):
      return self.root is not None and os.path.isdir ( self.root )
   # --- end of exists (...) ---

   __bool__ = exists

   def get_subdir ( self, relpath ):
      if self.root:
         return self.__class__ (
            fspath = ( self.root + os.sep + relpath ),
            name   = relpath,
            parent = self
         )
      else:
         return self
   # --- end of get_subdir (...) ---

   def get_obj_subdir ( self, obj ):
      return self.get_subdir ( obj.name )
   # --- end of get_obj_subdir (...) ---

   def __str__ ( self ):
      return self.root or ""
   # --- end of __str__ (...) ---


class _AdditionsDirView ( object ):

   def __init__ ( self, additions_dir ):
      self._additions_dir = additions_dir
   # --- end of __init__ (...) ---

   def __bool__ ( self ):
      return bool ( self._additions_dir )
   # --- end of __bool__ (...) ---


class _EbuildAdditionsView ( _AdditionsDirView ):

   def __init__ ( self, additions_dir ):
      super ( _EbuildAdditionsView, self ).__init__ (
         additions_dir=additions_dir
      )
      if hasattr ( self, 'prepare' ):
         self.prepare()
   # --- end of __init__ (...) ---

   def _get_files_with_suffix ( self, suffix ):
      assert '.' not in self._additions_dir.name

      fre = re.compile (
         self._additions_dir.name + '[-](?P<pvr>[0-9.]+([-]r[0-9]+)?)'
         + suffix.replace ( '.', '[.]' )
      )
      root = self._additions_dir.root
      for fname in os.listdir ( root ):
         fmatch = fre.match ( fname )
         if fmatch:
            yield ( fmatch.group ( 'pvr' ), ( root + os.sep + fname ), fname )
   # --- end of _get_files_with_suffix (...) ---


class PatchView ( _EbuildAdditionsView ):

   def has_patches ( self ):
      return bool ( getattr ( self, '_patches', None ) )
   # --- end of has_patches (...) ---

   def get_patches ( self, pvr ):
      patch = self._patches.get ( pvr, None )
      return ( patch, ) if patch is not None else None
   # --- end of get_patches (...) ---

   def prepare ( self ):
      if self._additions_dir.exists():
         # dict { pvr => patch_file }
         self._patches = {
            pvr: fpath
            for pvr, fpath, fname in self._get_files_with_suffix ( '.patch' )
         }
   # --- end of prepare (...) ---
