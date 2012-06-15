# R Overlay -- Manifest creation for ebuilds
# Copyright 2006-2012 Gentoo Foundation
# Distributed under the terms of the GNU General Public License v2


import logging

import roverlay.portage.manifesthelpers

_MANIFEST_IMPLEMENTATION = \
	roverlay.portage.manifesthelpers.ExternalManifestCreation


def create_manifest ( package_info, nofail=False ):
	"""Creates a Manifest for package_info, using the <<best>> implementation
	available.

	current implementation: ExternalManifestCreation (using ebuild(1))

	arguments:
	* package_info --
	* nofail -- catch exceptions and return False
	"""
	try:
		return _MANIFEST_IMPLEMENTATION.do ( package_info )
	except Exception as e:
		logging.exception ( e )
		if nofail:
			return False
		else:
			raise
# --- end of create_manifest (...) ---
