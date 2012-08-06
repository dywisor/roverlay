# R overlay -- config package, static
# -*- coding: utf-8 -*-
# Copyright (C) 2012 André Erdmann <dywi@mailerd.de>
# Distributed under the terms of the GNU General Public License;
# either version 2 of the License, or (at your option) any later version.

"""provides access to a static ConfigTree instance.

This modules defines the following functions:
* access      -- returns the static ConfigTree (and creates it if necessary)
* get_loader  -- returns a config data loader for the static ConfigTree
* get         -- looks up a key in the static ConfigTree
* get_or_fail -- like get(), but raises an Exception if key not found
"""

__all__ = [ 'access', 'get_loader', 'get', 'get_or_fail', ]

from roverlay.config.tree import ConfigTree

def access():
	"""Returns the static ConfigTree (and creates it, if necessary)."""
	return ConfigTree() if ConfigTree.instance is None else ConfigTree.instance
# --- end of access (...) ---

def get_loader():
	"""Returns a config entry loader for the static ConfigTree."""
	return access().get_loader()
# --- end of get_loader (...) ---

def get ( key, fallback_value=None, fail_if_unset=False ):
	"""Searches for key in the ConfigTree and returns its value if possible,
	else fallback_value.
	'key' is a config path [<section>[.<subsection>*]]<option name>.

	arguments:
	* key            --
	* fallback_value --
	* fail_if_unset  --
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
	"""Looks up key in the static ConfigTree and returns its value, if found,
	else raises an Exception.

	arguments:
	* key --
	"""
	return access().get_or_fail ( key )
# --- end of get_or_fail (...) ---
