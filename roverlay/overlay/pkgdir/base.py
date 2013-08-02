# R overlay -- overlay package, package directory
# -*- coding: utf-8 -*-
# Copyright (C) 2012 André Erdmann <dywi@mailerd.de>
# Distributed under the terms of the GNU General Public License;
# either version 2 of the License, or (at your option) any later version.

__all__ = [ 'create', 'get_class', ]

import logging

import roverlay.config

import roverlay.overlay.pkgdir.packagedir_base
import roverlay.overlay.pkgdir.packagedir_ebuildmanifest
import roverlay.overlay.pkgdir.packagedir_newmanifest


_package_dir_class  = None

_PACKAGE_DIR_IMPLEMENTATIONS = {
   'none'    : roverlay.overlay.pkgdir.packagedir_base.PackageDirBase,
   'default' : roverlay.overlay.pkgdir.packagedir_newmanifest.PackageDir,
   'e'       : roverlay.overlay.pkgdir.packagedir_ebuildmanifest.PackageDir,
   'ebuild'  : roverlay.overlay.pkgdir.packagedir_ebuildmanifest.PackageDir,
   'next'    : roverlay.overlay.pkgdir.packagedir_newmanifest.PackageDir,
}

def _configure():
   """Determines which Manifest implementation to use and sets the
   _package_dir_module, _package_dir_class variables accordingly.
   """
   mf_impl = roverlay.config.get_or_fail ( 'OVERLAY.manifest_implementation' )

   if mf_impl in _PACKAGE_DIR_IMPLEMENTATIONS:
      global _package_dir_class
      _package_dir_class = _PACKAGE_DIR_IMPLEMENTATIONS [mf_impl]

      if hasattr ( _package_dir_class, 'init_cls' ):
         _package_dir_class.init_cls()
      else:
         _package_dir_class.init_base_cls()

      logging.getLogger ('pkgdir').debug (
         'Using {!r} as manifest implementation.'.format ( mf_impl )
      )
   else:
      # NameError, NotImplementedError, ...?
      raise Exception (
         "PackageDir/Manifest implementation {} is unknown".format ( mf_impl )
      )
# --- end of configure (...) ---

def get_class():
   """Returns the configured PackageDir class."""
   if _package_dir_class is None:
      _configure()
   return _package_dir_class
# --- end of get_class (...) ---

def create ( *args, **kwargs ):
   """Returns a new PackageDir object by calling the constructor
   of the configured PackageDir class (as returned by get_class()).
   """
   return get_class() ( *args, **kwargs )
# --- end of create (...) ---
