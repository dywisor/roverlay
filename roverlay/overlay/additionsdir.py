# R overlay -- overlay package, overlay additions dir
# -*- coding: utf-8 -*-
# Copyright (C) 2013 André Erdmann <dywi@mailerd.de>
# Distributed under the terms of the GNU General Public License;
# either version 2 of the License, or (at your option) any later version.

import os
import re

EMPTY_TUPLE = ()

class AdditionsDir ( object ):
   """AdditionsDir represents a filesystem directory (that does not need
   to exist).
   """

   def __init__ ( self, fspath, name=None, parent=None ):
      self.root   = str ( fspath ) if fspath else None
      self.parent = parent
      self.name   = name
   # --- end of __init__ (...) ---

   def exists ( self ):
      return self.root is not None and os.path.isdir ( self.root )
   # --- end of exists (...) ---

   __bool__ = exists

   def iter_entries ( self ):
      """Generator that yields the directory content of this dir."""
      if self.exists():
         for name in os.listdir ( self.root ):
            yield ( name, ( self.root + os.sep + name ) )
   # --- end of iter_entries (...) ---

   def __iter__ ( self ):
      return iter ( self.iter_entries() )
   # --- end of __iter__ (...) ---

   def get_child ( self, fspath, name ):
      """Returns a new instance with the given fspath/name and this object
      as parent.
      arguments:

      * fspath --
      * name   --
      """
      return self.__class__ (
         fspath = fspath,
         name   = name,
         parent = self
      )
   # --- end of get_child (...) ---

   def get_subdir ( self, relpath ):
      """Returns a new instance which represents a subdirectory of this dir.

      arguments:
      * relpath -- path of the new instance, relative to the root of this dir
      """
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
      """Like get_obj_subdir(), but uses obj.name as relpath.

      arguments:
      * obj --
      """
      return self.get_subdir ( obj.name )
   # --- end of get_obj_subdir (...) ---

   def __str__ ( self ):
      return self.root or ""
   # --- end of __str__ (...) ---

# --- end of AdditionsDir ---


class _AdditionsDirView ( object ):
   """view objects implement AdditionsDir actions, e.g. find certain files."""

   def __init__ ( self, additions_dir ):
      self._additions_dir = additions_dir
   # --- end of __init__ (...) ---

   def __bool__ ( self ):
      return bool ( self._additions_dir )
   # --- end of __bool__ (...) ---

   @property
   def name ( self ):
      return self._additions_dir.name
   # --- end of name (...) ---

   def _fs_iter_regex ( self, regex ):
      """Iterates over the content of the additions dir and yields
      3-tuples ( match, path, name ) for each name that matches the given
      regex.

      arguments:
      * regex --
      """
      fre = re.compile ( regex )

      for name, fspath in self._additions_dir:
         fmatch = fre.match ( name )
         if fmatch:
            yield ( fmatch, fspath, name )
   # --- end of _fs_iter_regex (...) ---

# --- end of _AdditionsDirView ---


class _EbuildAdditionsView ( _AdditionsDirView ):

   # with leading '-'
   RE_PVR = '[-](?P<pvr>[0-9].*?([-]r[0-9]+)?)'

   def __init__ ( self, additions_dir ):
      """Ebuild additions dir view constructor.
      Also calls prepare() if declared.

      arguments:
      * additions_dir --
      """
      super ( _EbuildAdditionsView, self ).__init__ (
         additions_dir=additions_dir
      )
      if hasattr ( self, 'prepare' ): self.prepare()
   # --- end of __init__ (...) ---

# --- end of _EbuildAdditionsView ---


class EbuildView ( _EbuildAdditionsView ):
   """View object for finding/importing ebuilds."""

   RE_EBUILD_SUFFIX = '[.]ebuild'

   def has_ebuilds ( self ):
      """Returns True if there are any ebuilds that could be imported."""
      return bool ( getattr ( self, '_ebuilds', None ) )
   # --- end of has_ebuilds (...) ---

   def get_ebuilds ( self ):
      """Returns all ebuilds as list of 3-tuples ( pvr, path, name )."""
      return self._ebuilds
   # --- end of get_ebuilds (...) ---

   def has_metadata_xml ( self ):
      return bool ( getattr ( self, '_metadata_xml', None ) )
   # --- end of has_metadata_xml (...) ---

   def get_metadata_xml ( self ):
      return self._metadata_xml
   # --- end of get_metadata_xml (...) ---

   def __iter__ ( self ):
      return iter ( self.get_ebuilds() )
   # --- end of __iter__ (...) ---

   def prepare ( self ):
      """Searches for ebuilds and create self._ebuilds."""
      if self._additions_dir.exists():
         ebuilds = list()

         for fmatch, fpath, fname in self._fs_iter_regex (
            self._additions_dir.name + self.RE_PVR + self.RE_EBUILD_SUFFIX
         ):
            # deref symlinks
            ebuilds.append (
               ( fmatch.group ( 'pvr' ), os.path.abspath ( fpath ), fname )
            )

         self._ebuilds = ebuilds

         metadata_xml = self._additions_dir.root + os.sep + 'metadata.xml'
         if os.path.isfile ( metadata_xml ):
            self._metadata_xml = metadata_xml
         else:
            self._metadata_xml = None
   # --- end of prepare (...) --

# --- end of EbuildView ---


class CategoryView ( _AdditionsDirView ):
   """View object that creates EbuildView objects."""

   def iter_packages ( self ):
      for name, fspath in self._additions_dir:
         if os.path.isdir ( fspath ):
            yield EbuildView (
               self._additions_dir.get_child ( fspath, name )
            )
   # --- end of iter_packages (...) ---

   def __iter__ ( self ):
      return iter ( self.iter_packages() )
   # --- end of __iter__ (...) ---

# --- end of CategoryView ---


class CategoryRootView ( _AdditionsDirView ):
   """View object that creates CategoryView objects."""

   def iter_categories ( self ):
      for name, fspath in self._additions_dir:
         if os.path.isdir ( fspath ) and (
            '-' in name or name == 'virtual'
         ):
            yield CategoryView (
               self._additions_dir.get_child ( fspath, name )
            )
   # --- end of iter_categories (...) ---

   def __iter__ ( self ):
      return iter ( self.iter_categories() )
   # --- end of __iter__ (...) ---

# --- end of CategoryRootView ---


class PatchView ( _EbuildAdditionsView ):
   """View object for finding ebuild patches."""

   RE_PATCH_SUFFIX = '(?P<patchno>[0-9]{4})?[.]patch'

   def has_patches ( self ):
      """Returns True if one or more patches are available."""
      return bool ( getattr ( self, '_patches', None ) )
   # --- end of has_patches (...) ---

   def get_patches ( self, pvr, fallback_to_default=True ):
      """Returns a list of patches that should be applied to the ebuild
      referenced by pvr.

      arguments:
      * pvr                 -- $PVR of the ebuild
      * fallback_to_default -- return default patches if no version-specific
                               ones are available (defaults to True)
      """
      patches = self._patches.get ( pvr, None )
      if patches:
         return patches
      elif fallback_to_default:
         return getattr ( self, '_default_patches', EMPTY_TUPLE )
      else:
         return EMPTY_TUPLE
   # --- end of get_patches (...) ---

   def get_default_patches ( self ):
      """Returns the default patches."""
      return getattr ( self, '_default_patches', EMPTY_TUPLE )
   # --- end of get_default_patches (...) ---

   def prepare ( self ):
      """Searches for ebuild patch files."""
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

            if patchno in self._patches:
               if len ( self._patches [patchno] ) < 2:

                  del self._patches [patchno]
                  default_patches.append (
                     ( ( -1 if patchno is None else int ( patchno ) ), fpath )
                  )
               else:
                  pass
            else:
               default_patches.append (
                  ( ( -1 if patchno is None else int ( patchno ) ), fpath )
               )
         # -- end for;

         if default_patches:
            self._default_patches = patchno_sort ( default_patches )
   # --- end of prepare (...) ---

# --- end of PatchView ---
