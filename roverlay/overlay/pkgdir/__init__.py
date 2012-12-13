# R overlay -- overlay package, package directory (<??>)
# -*- coding: utf-8 -*-
# Copyright (C) 2012 André Erdmann <dywi@mailerd.de>
# Distributed under the terms of the GNU General Public License;
# either version 2 of the License, or (at your option) any later version.

__all__ = [ 'create', 'get_class', ]

# the actual PackageDir implementation will be loaded after initialization
# of the config module (using importlib.import_module)
import importlib

import logging

import roverlay.config


# _package_dir_module is an imported module or None
_package_dir_module = None
_package_dir_class  = None

_PACKAGE_DIR_IMPLEMENTATIONS = {
   'none'             : 'packagedir_base',
   'default'          : 'packagedir_ebuildmanifest',
   'external:ebuild'  : 'packagedir_ebuildmanifest',
#   'external:portage' : 'packagedir_portagemanifest',
#   'internal'         : NotImplemented,
}

def _configure():
   mf_impl = roverlay.config.get (
      'OVERLAY.manifest_implementation',
      _PACKAGE_DIR_IMPLEMENTATIONS ['default']
   )

   pkgdir_impl = _PACKAGE_DIR_IMPLEMENTATIONS.get ( mf_impl, None )

   if pkgdir_impl is not None:
      global _package_dir_module
      _package_dir_module = importlib.import_module (
         'roverlay.overlay.pkgdir.' + pkgdir_impl
      )

      global _package_dir_class
      if hasattr ( _package_dir_module, 'PackageDir' ):
         _package_dir_class = _package_dir_module.PackageDir
      else:
         _package_dir_class = _package_dir_module.PackageDirBase

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
   if _package_dir_class is None:
      _configure()
   return _package_dir_class
# --- end of get_class (...) ---

def create ( *args, **kwargs ):
   return get_class() ( *args, **kwargs )
# --- end of create (...) ---
