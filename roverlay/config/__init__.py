# R overlay -- config module
# Copyright 2006-2012 Gentoo Foundation
# Distributed under the terms of the GNU General Public License v2

from roverlay.config.tree import ConfigTree

CONFIG_INJECTION_IS_BAD = True

def access():
	"""Returns the ConfigTree."""
	return ConfigTree() if ConfigTree.instance is None else ConfigTree.instance
# --- end of access (...) ---

def loader():
	return access().get_loader()
# --- end of get_loader (...) ---

def get ( key, fallback_value=None, fail_if_unset=False ):
	"""Searches for key in the ConfigTree and returns its value if possible,
	else fallback_value.
	'key' is a config path [<section>[.<subsection>*]]<option name>.

	arguments:
	* key --
	* fallback_value --
	"""
	if not fallback_value is None:
		return access().get (
			key, fallback_value=fallback_value, fail_if_unset=fail_if_unset
		)
	else:
		return access().get (
			key, fallback_value=None, fail_if_unset=fail_if_unset
		)
# --- end of get (...) ---

def get_or_fail ( key ):
	return access().get ( key, fail_if_unset=True )
# --- end of get_or_fail (...) ---
