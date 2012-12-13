# R overlay -- overlay package, package directory
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

	def write_manifest ( self, ignore_empty=False ):
		"""Generates and writes the Manifest file for this package.

		expects: called after writing metadata/ebuilds

		returns: success (True/False)

		raises:
		* Exception if no ebuild exists
		"""

		# it should be sufficient to call create_manifest for one ebuild,
		#  choosing the latest one that exists in self.physical_location and
		#  has enough data (DISTDIR, EBUILD_FILE) for this task.
		#  Additionally, all DISTDIRs (multiple repos, sub directories) have
		#  to be collected and passed to Manifest creation.
		#  => collect suitable PackageInfo objects from self._packages
		#
		pkgs_for_manifest = tuple (
			p for p in self._packages.values() \
			if p.has ( 'distdir', 'ebuild_file' )
		)

		if pkgs_for_manifest:
			if manifest.create_manifest ( pkgs_for_manifest, nofail=False ):
				self._need_manifest = False
				return True
		elif ignore_empty:
			return True
		else:
			raise Exception (
				'In {mydir}: No ebuild written so far! '
				'I really don\'t know what do to!'.format (
					mydir=self.physical_location
			) )

		return False
	# --- end of write_manifest (...) ---
