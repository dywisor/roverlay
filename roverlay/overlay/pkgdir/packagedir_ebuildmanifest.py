# R overlay -- overlay package, package directory (ebuild manifest)
# -*- coding: utf-8 -*-
# Copyright (C) 2012 André Erdmann <dywi@mailerd.de>
# Distributed under the terms of the GNU General Public License;
# either version 2 of the License, or (at your option) any later version.

__all__ = [ 'PackageDir', ]

import threading

import roverlay.config
import roverlay.tools.ebuild
import roverlay.tools.ebuildenv
import roverlay.overlay.pkgdir.packagedir_base
import roverlay.overlay.pkgdir.distroot.static


class PackageDir ( roverlay.overlay.pkgdir.packagedir_base.PackageDirBase ):
   """
   PackageDir class that uses the ebuild executable for Manifest writing.
   """
   #DISTROOT            = None
   #MANIFEST_ENV        = None
   MANIFEST_LOCK       = threading.Lock()
   MANIFEST_THREADSAFE = False

   @classmethod
   def init_cls ( cls ):
      env = roverlay.tools.ebuildenv.ManifestEnv()
      env.add_overlay_dir ( roverlay.config.get_or_fail ( 'OVERLAY.dir' ) )

      cls.DISTROOT = (
         roverlay.overlay.pkgdir.distroot.static.get_configured ( static=True )
      )

      cls.MANIFEST_ENV = env
   # --- end of init_cls (...) ---

   def _write_manifest ( self, pkgs_for_manifest ):
      """Generates and writes the Manifest file for this package.

      expects: called after writing metadata/ebuilds

      returns: success (True/False)
      """
      try:
         self.MANIFEST_LOCK.acquire()

         # choosing one ebuild for calling "ebuild <ebuild>" is sufficient
         ebuild_file = pkgs_for_manifest [0] ['ebuild_file']

         distdir = self.DISTROOT.get_distdir ( pkgs_for_manifest [0] ['name'] )

         # add hardlinks to DISTROOT (replacing existing files/links)
         for p in pkgs_for_manifest:
            # TODO: optimize this further?
            # -> "not has physical_only?"
            #     (should be covered by "has package_file")
            distdir.add ( p ['package_file'], p ['package_src_destpath'] )


         if roverlay.tools.ebuild.doebuild_manifest (
            ebuild_file, self.logger,
            self.MANIFEST_ENV.get_env ( distdir.get_root() )
         ):
            self.logger.debug ( "Manifest written." )
            ret = True

         else:
            self.logger.error (
               'Couldn\'t create Manifest for {ebuild}! '
               'Return code was {ret}.'.format (
                  ebuild=ebuild_file, ret=ebuild_call.returncode
               )
            )
            ret = False

      except Exception as err:
         self.logger.exception ( err )
         raise

      finally:
         self.MANIFEST_LOCK.release()

      return ret
   # --- end of write_manifest (...) ---
