# R overlay -- overlay package, overlay additions dir
# -*- coding: utf-8 -*-
# Copyright (C) 2013 André Erdmann <dywi@mailerd.de>
# Distributed under the terms of the GNU General Public License;
# either version 2 of the License, or (at your option) any later version.

import os
import re

EMPTY_TUPLE = ()


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

   # with leading '-'
   RE_PVR = '[-](?P<pvr>[0-9.]+([-]r[0-9]+)?)'

   def __init__ ( self, additions_dir ):
      super ( _EbuildAdditionsView, self ).__init__ (
         additions_dir=additions_dir
      )
      if hasattr ( self, 'prepare' ):
         self.prepare()
   # --- end of __init__ (...) ---

   def _fs_iter_regex ( self, regex ):
      fre = re.compile ( regex )

      root = self._additions_dir.root
      for fname in os.listdir ( root ):
         fmatch = fre.match ( fname )
         if fmatch:
            yield ( fmatch, ( root + os.sep + fname ), fname )
   # --- end of _fs_iter_regex (...) ---


class EbuildView ( _EbuildAdditionsView ):

   RE_EBUILD_SUFFIX = '[.]ebuild'

   def has_ebuilds ( self ):
      return bool ( getattr ( self, '_ebuilds', None ) )
   # --- end of has_ebuilds (...) ---

   def get_ebuilds ( self ):
      return self._ebuilds
   # --- end of get_ebuilds (...) ---

   def __iter__ ( self ):
      return iter ( self.get_ebuilds )
   # --- end of __iter__ (...) ---

   def _prepare ( self ):
      if self._additions_dir.exists():
         ebuilds = list()

         for fmatch, fpath, fname in self._fs_iter_regex (
            self._additions_dir.name + self.RE_PVR + self.RE_EBUILD_SUFFIX
         ):
            # deref symlinks
            ebuilds.append (
               fmatch.group ( 'pvr' ), os.path.abspath ( fpath ), fname
            )
   # --- end of _prepare (...) --



class PatchView ( _EbuildAdditionsView ):

   RE_PATCH_SUFFIX = '(?P<patchno>[0-9]{4})?[.]patch'

   def has_patches ( self ):
      return bool ( getattr ( self, '_patches', None ) )
   # --- end of has_patches (...) ---

   def get_patches ( self, pvr, fallback_to_default=True ):
      patches = self._patches.get ( pvr, None )
      if patches:
         return patches
      elif fallback_to_default:
         return getattr ( self, '_default_patches', EMPTY_TUPLE )
      else:
         return EMPTY_TUPLE
   # --- end of get_patches (...) ---

   def get_default_patches ( self ):
      return getattr ( self, '_default_patches', EMPTY_TUPLE )
   # --- end of get_default_patches (...) ---

   def prepare ( self ):
      def patchno_sort ( iterable ):
         return list (
            v[1] for v in sorted ( iterable, key=lambda k: k[0] )
         )
      # --- end of patchno_sort (...) ---

      if self._additions_dir.exists():
         # dict { pvr => *(patch_no, patch_file) }
         patches = dict()


         # find version-specific patches
         for fmatch, fpath, fname in self._fs_iter_regex (
            self._additions_dir.name + self.RE_PVR + self.RE_PATCH_SUFFIX
         ):
            patchno = fmatch.group ( 'patchno' )
            patchno = -1 if patchno is None else int ( patchno )
            pvr     = fmatch.group ( 'pvr' )
            if pvr in patches:
               patches [pvr].append ( ( patchno, fpath ) )
            else:
               patches [pvr] = [ ( patchno, fpath ) ]

         # -- end for;

         self._patches = { k: patchno_sort ( v ) for k, v in patches.items() }


         # find default patches

         default_patches = []

         for fmatch, fpath, fname in self._fs_iter_regex (
            self._additions_dir.name + self.RE_PATCH_SUFFIX
         ):
            patchno = fmatch.group ( 'patchno' )

            default_patches.append (
               ( ( -1 if patchno is None else int ( patchno ) ), fpath )
            )
         # -- end for;

         if default_patches:
            self._default_patches = patchno_sort ( default_patches )
   # --- end of prepare (...) ---
