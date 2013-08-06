# R overlay -- overlay package, package directory (ebuild manifest)
# -*- coding: utf-8 -*-
# Copyright (C) 2012 André Erdmann <dywi@mailerd.de>
# Distributed under the terms of the GNU General Public License;
# either version 2 of the License, or (at your option) any later version.

__all__ = [ 'PackageDir', ]


import roverlay.overlay.pkgdir.packagedir_base


class PackageDir ( roverlay.overlay.pkgdir.packagedir_base.PackageDirBase ):
   """
   PackageDir class that uses the ebuild executable for Manifest writing.
   """
   MANIFEST_THREADSAFE = False


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
      return self.do_ebuildmanifest ( pkg ['ebuild_file'] )
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

      return self.do_ebuildmanifest ( ebuild_file, distdir )
   # --- end of write_manifest (...) ---

# --- end of PackageDir #ebuildmanifest ---
