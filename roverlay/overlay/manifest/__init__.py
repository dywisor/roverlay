# R Overlay -- Manifest creation for ebuilds
# Copyright 2006-2012 Gentoo Foundation
# Distributed under the terms of the GNU General Public License v2
import logging
import threading

from roverlay.overlay.manifest import helpers

_manifest_creation = helpers.ExternalManifestCreation()
# ExternalManifestCreation does not support threads (-> multiprocesses)
# for one directory/overlay
_manifest_lock = threading.Lock()

def create_manifest ( package_info_list, nofail=False ):
	"""Creates a Manifest for package_info, using the <<best>> implementation
	available.

	current implementation: ExternalManifestCreation (using ebuild(1))

	arguments:
	* package_info --
	* nofail -- catch exceptions and return False
	"""
	ret = False
	try:
		_manifest_lock.acquire()
		ret = _manifest_creation.create_for ( package_info_list )
	except Exception as e:
		logging.exception ( e )
		if nofail:
			ret = False
		else:
			raise
	finally:
		_manifest_lock.release()

	return ret
# --- end of create_manifest (...) ---
