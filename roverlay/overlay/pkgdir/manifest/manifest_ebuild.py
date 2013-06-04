# R overlay -- manifest package, manifest helpers (actual implementation)
# -*- coding: utf-8 -*-
# Copyright (C) 2012 André Erdmann <dywi@mailerd.de>
# Distributed under the terms of the GNU General Public License;
# either version 2 of the License, or (at your option) any later version.

"""manifest helpers (actual implementation)

This module implements Manifest creation using ebuild(1).
"""

__all__ = [ 'ExternalManifestCreation', ]

import os.path
import copy
import logging
import subprocess


import roverlay.overlay.pkgdir.distroot.static

from roverlay import config, strutil

from roverlay.overlay.pkgdir.manifest.env import ManifestEnv

class ExternalManifestCreation ( object ):
   """This class implements Manifest creation using the low level ebuild
   interface, ebuild(1), which is called in a filtered environment.
   """
   # NOTE:
   # ebuild <ebuild> digest does not support multiprocesses for one overlay,

   def _doinit ( self ):
      """Initializes self's data, needs an initialized ConfigTree."""
      self.manifest_env = ManifestEnv.get_new()
      self.ebuild_tgt   = config.get ( 'TOOLS.EBUILD.target', 'manifest' )
      self.ebuild_prog  = config.get ( 'TOOLS.EBUILD.prog', '/usr/bin/ebuild' )

      # set PORDIR_OVERLAY and DISTDIR
      self.manifest_env ['PORTDIR_OVERLAY'] = config.get_or_fail (
         'OVERLAY.dir'
      )
      # self.distroot[.get_distdir(...)] replaces the __tmp__ directory
      self.distroot = (
         roverlay.overlay.pkgdir.distroot.static.get_configured ( static=True )
      )

      self._initialized = True
   # --- end of _doinit (...) ---

   def __init__ ( self, lazy_init=False ):
      self.logger = logging.getLogger ( 'ManifestCreation' )
      self._initialized = False
      if not lazy_init:
         self._doinit()
   # --- end of __init__ (...) ---

   def create_for ( self, package_info_list ):
      """See ManifestCreation.create_for.
      Calls ebuild, returns True on success else False.

      raises: *passes Exceptions from failed config lookups
      """
      if not self._initialized:
         self._doinit()

      # choosing one ebuild for calling "ebuild <ebuild>" is sufficient
      ebuild_file = package_info_list [0] ['ebuild_file']

      distdir = self.distroot.get_distdir ( package_info_list [0] ['name'] )

      #
      self.manifest_env ['DISTDIR'] = distdir.get_root()

      # add hardlinks to DISTROOT (replacing existing files/links)
      for p in package_info_list:
         # TODO: optimize this further?
         # -> "not has physical_only?"
         #     (should be covered by "has package_file")
         distdir.add ( p ['package_file'] )

      ebuild_call = subprocess.Popen (
         (
            self.ebuild_prog,
            ebuild_file,
            self.ebuild_tgt
         ),
         stdin=None,
         stdout=subprocess.PIPE,
         stderr=subprocess.PIPE,
         env=self.manifest_env
      )

      output = ebuild_call.communicate()

      # log stderr
      for line in strutil.pipe_lines ( output [1], use_filter=True ):
         self.logger.warning ( line )

      if ebuild_call.returncode == 0:
         self.logger.debug ( "Manifest written." )
         return True
      else:
         self.logger.error (
            'Couldn\'t create Manifest for {ebuild}! '
            'Return code was {ret}.'.format (
               ebuild=ebuild_file, ret=ebuild_call.returncode
            )
         )
         return False
   # --- end of create_for (...) ---
