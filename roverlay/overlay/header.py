# R overlay -- overlay package, ebuild header
# -*- coding: utf-8 -*-
# Copyright (C) 2012 André Erdmann <dywi@mailerd.de>
# Distributed under the terms of the GNU General Public License;
# either version 2 of the License, or (at your option) any later version.

"""ebuild header

This module provides one class, EbuildHeader, that is used to create ebuild
headers ("copyright..., inherit...").
"""

class EbuildHeader ( object ):
	def __init__ ( self, default_header ):
		self.default_header = default_header
		self.eclasses       = ()

		self._cached_header = None
	# --- end of __init__ (...) ---

	def set_eclasses ( self, eclass_names ):
		self.eclasses = eclass_names
	# --- end of set_eclasses (...) ---

	def get ( self, use_cached=True ):
		if self._cached_header is None or not use_cached:
			self._cached_header = self._make()
		return self._cached_header
	# --- end of get (...) ---

	def _make ( self ):
		if self.eclasses:
			inherit = 'inherit ' + ' '.join ( sorted ( self.eclasses ) )
		else:
			inherit = None

		# header and inherit is expected and therefore the first condition here
		if inherit and self.default_header:
			return self.default_header + '\n' + inherit

		elif inherit:
			return inherit

		elif self.default_header:
			return self.default_header

		else:
			return None
	# --- end of _make (...) ---
