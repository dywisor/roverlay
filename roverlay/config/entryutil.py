# R overlay -- config package, entryutil
# -*- coding: utf-8 -*-
# Copyright (C) 2012 André Erdmann <dywi@mailerd.de>
# Distributed under the terms of the GNU General Public License;
# either version 2 of the License, or (at your option) any later version.

"""provides config utility functions that are normally not needed."""

__all__ = [ 'list_entries', ]

import re
import textwrap

from roverlay.config.entrymap import CONFIG_ENTRY_MAP

def _iter_entries():
	"""Iterates through all entries in CONFIG_ENTRY_MAP and yields config
	entry information (entry name, description).
	"""
	for entry_key, entry in CONFIG_ENTRY_MAP.items():
		name = entry_key.upper()
		if entry is None:
			# entry is disabled
			pass
		elif isinstance ( entry, dict ):
			if 'description' in entry:
				yield ( name, entry ['description'] )
			elif 'desc' in entry:
				yield ( name, entry ['desc'] )
			else:
				yield ( name, )
		elif isinstance ( entry, str ) and entry:
			yield ( name, "alias to " + entry.upper() )
		else:
			yield ( name, )


def list_entries ( newline_after_entry=True ):
	"""Returns a string that lists (and describes) all config entries.

	arguments:
	* newline_after_entry -- insert an empty line after each config entry
	"""
	wrapper = textwrap.TextWrapper (
		initial_indent    = 2 * ' ',
		subsequent_indent = 3 * ' ',
		#width = 75,
	)
	remove_ws = re.compile ( "\s+" )
	wrap = wrapper.wrap

	lines = list()
	for entry in sorted ( _iter_entries(), key = lambda x : x[0] ):
		lines.append ( entry [0] )
		if len ( entry ) > 1:
			lines.extend ( wrap ( remove_ws.sub ( ' ', entry [1] ) ) )

		if newline_after_entry:
			lines.append ( '' )

	return '\n'.join ( lines )
