# R overlay -- overlay package, package directory (ebuild manifest)
# -*- coding: utf-8 -*-
# Copyright (C) 2012 André Erdmann <dywi@mailerd.de>
# Distributed under the terms of the GNU General Public License;
# either version 2 of the License, or (at your option) any later version.

__all__ = [ 'PackageDir', ]

import os
import threading


import roverlay.config
import roverlay.tools.ebuild
import roverlay.tools.ebuildenv

import roverlay.overlay.pkgdir.packagedir_base


class PackageDir ( roverlay.overlay.pkgdir.packagedir_base.PackageDirBase ):
   """
   PackageDir class that uses the ebuild executable for Manifest writing.
   """
   #MANIFEST_ENV        = None
   MANIFEST_THREADSAFE = False

   @classmethod
   def init_cls ( cls ):
      cls.init_base_cls()

      env = roverlay.tools.ebuildenv.ManifestEnv()
      env.add_overlay_dir ( roverlay.config.get_or_fail ( 'OVERLAY.dir' ) )
      cls.MANIFEST_ENV = env
   # --- end of init_cls (...) ---

   def _do_ebuildmanifest ( self, ebuild_file, distdir=None ):
      """Calls doebuild_manifest().
      Returns True on success, else False. Also handles result logging.

      arguments:
      * ebuild_file -- ebuild file that should be used for the doebuild call
      * distdir     -- distdir object (optional)
      """
      try:
         call = roverlay.tools.ebuild.doebuild_manifest (
            ebuild_file, self.logger,
            self.MANIFEST_ENV.get_env (
               distdir.get_root() if distdir is not None else (
               self.DISTROOT.get_distdir ( self.name ).get_root()
               )
            ),
            return_success=False
         )
      except Exception as err:
         self.logger.exception ( err )
         raise
      # -- end try

      if call.returncode == os.EX_OK:
         self.logger.debug ( "Manifest written." )
         return True
      else:
         self.logger.error (
            'Couldn\'t create Manifest for {ebuild}! '
            'Return code was {ret}.'.format (
               ebuild=ebuild_file, ret=call.returncode
            )
         )
         return False
   # --- end of _do_ebuildmanifest (...) ---

   def _write_import_manifest ( self ):
      """Writes a Manifest file if this package has any imported ebuilds.

      Returns True if a Manifest has been written, else False.
      """
      try:
         pkg = next (
            p for p in self._packages.values()
            if p.has ( 'imported', 'ebuild_file' )
         )
      except StopIteration:
         # no imported ebuilds
         return False
      # -- end try

      self.logger.debug ( "Writing (import-)Manifest" )
      return self._do_ebuildmanifest ( pkg ['ebuild_file'] )
   # --- end of _write_import_manifest (...) ---

   def _write_manifest ( self, pkgs_for_manifest ):
      """Generates and writes the Manifest file for this package.

      expects: called after writing metadata/ebuilds

      returns: success (True/False)
      """
      # choosing one ebuild for calling "ebuild <ebuild>" is sufficient
      ebuild_file = pkgs_for_manifest [0] ['ebuild_file']
      distdir     = self.DISTROOT.get_distdir ( self.name )

      # add hardlinks to DISTROOT (replacing existing files/links)
      for p in pkgs_for_manifest:
         # TODO: optimize this further?
         # -> "not has physical_only?"
         #     (should be covered by "has package_file")
         p.make_distmap_hash()
         distdir.add ( p ['package_file'], p ['package_src_destpath'], p )
      # -- end for;

      return self._do_ebuildmanifest ( ebuild_file, distdir )
   # --- end of write_manifest (...) ---

# --- end of PackageDir #ebuildmanifest ---
