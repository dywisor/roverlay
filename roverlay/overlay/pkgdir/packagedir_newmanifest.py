# R overlay -- overlay package, package directory ("new" manifest)
# -*- coding: utf-8 -*-
# Copyright (C) 2013 André Erdmann <dywi@mailerd.de>
# Distributed under the terms of the GNU General Public License;
# either version 2 of the License, or (at your option) any later version.

__all__ = [ 'PackageDir', ]

import os
import threading


import roverlay.config

import roverlay.tools.ebuild

import roverlay.overlay.pkgdir.manifest.file
import roverlay.overlay.pkgdir.packagedir_base

from roverlay.overlay.pkgdir.manifest.file import ManifestFile


class PackageDir ( roverlay.overlay.pkgdir.packagedir_base.PackageDirBase ):
   """
   PackageDir class that uses an (mostly) internal implementation
   for Manifest writing.
   """

   MANIFEST_THREADSAFE = True

   HASH_TYPES = frozenset ( ManifestFile.HASH_TYPES )

   # Manifest entries for imported ebuilds have to be created during import
   DOEBUILD_FETCH = roverlay.tools.ebuild.doebuild_fetch_and_manifest

   def _get_manifest ( self ):
      """Returns a ManifestFile object."""
      manifest = ManifestFile ( self.physical_location )
      manifest.read ( ignore_missing=True )
      return manifest
   # --- end of _get_manifest (...) ---

   def _write_import_manifest ( self, _manifest=None ):
      """Verifies that Manifest file entries exist for all imported ebuilds.

      Assumption: ebuild file in Manifest => $SRC_URI, too

      Returns True on success, else False.

      arguments:
      * _manifest -- manifest object (defaults to None -> create a new one)
      """
      manifest = self._get_manifest() if _manifest is None else _manifest

      self.logger.debug ( "Checking import Manifest entries" )

      ret   = True
      ename = None
      for p in self._packages.values():
         efile = p.get ( 'ebuild_file' )
         if efile is not None:
            ename = os.path.basename ( efile )
            if manifest.has_entry ( 'EBUILD', ename ):
               self.logger.debug (
                  "manifest entry for {} is ok.".format ( ename )
               )
            else:
               ret = False
               self.logger.error (
                  "manifest entry for imported ebuild {} is missing!".format (
                     ename
                  )
               )
      # -- end for;
      return ret
   # --- end of _write_import_manifest (...) ---

   def _write_manifest ( self, pkgs_for_manifest ):
      """Generates and writes the Manifest file for this package.

      expects: called after writing metadata/ebuilds

      returns: success (True/False)
      """
      manifest = self._get_manifest()

      manifest.add_metadata_entry ( ignore_missing=True )

      # add manifest entries and add hardlinks to DISTROOT
      #  (replacing existing files/links)
      #
      distdir = self.DISTROOT.get_distdir ( self.name )
      for p in pkgs_for_manifest:
         # order is important here
         # add_package_entry() calls multihash with all required digests
         manifest.add_package_entry ( p )
         distdir.add ( p ['package_file'], p ['package_src_destpath'], p )
      # -- end for;

      #return (...)
      if (
         manifest.write ( force=True )
         and self._write_import_manifest ( _manifest=manifest )
      ):
         return True
      else:
         return False
   # --- end of write_manifest (...) ---

# --- end of PackageDir #ebuildmanifest ---
