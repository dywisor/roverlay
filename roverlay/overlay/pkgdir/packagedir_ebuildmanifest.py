# R overlay -- overlay package, package directory (ebuild manifest)
# -*- coding: utf-8 -*-
# Copyright (C) 2012 André Erdmann <dywi@mailerd.de>
# Distributed under the terms of the GNU General Public License;
# either version 2 of the License, or (at your option) any later version.

__all__ = [ 'PackageDir', ]

from roverlay.overlay.pkgdir import manifest
from roverlay.overlay.pkgdir import packagedir_base


class PackageDir ( packagedir_base.PackageDirBase ):
	"""
	PackageDir class that uses the ebuild executable for Manifest writing.
	"""

	MANIFEST_THREADSAFE = False

	def _write_manifest ( self, pkgs_for_manifest ):
		"""Generates and writes the Manifest file for this package.

		expects: called after writing metadata/ebuilds

		returns: success (True/False)
		"""

		return manifest.create_manifest ( pkgs_for_manifest, nofail=False )
	# --- end of write_manifest (...) ---
