# R Overlay -- dependency resolution, static resolver access
# Copyright 2006-2012 Gentoo Foundation
# Distributed under the terms of the GNU General Public License v2

from roverlay.depres.channels    import EbuildJobChannel
from roverlay.depres.depresolver import DependencyResolver

_RESOLVER = None

def resolver():
	"""Returns the resolver."""
	global _RESOLVER
	if _RESOLVER is None:
		_RESOLVER = DependencyResolver()
	return _RESOLVER
# --- end of resolver (...) ---

def get_ebuild_channel ( name=None, logger=None ):
	"""Returns a communication channel to the dependency resolver.

	arguments:
	name --
	logger --
	"""
	return resolver().register_channel (
		EbuildJobChannel ( name=name, logger=logger )
	)

# --- end of get_resolver_channel (...) ---
