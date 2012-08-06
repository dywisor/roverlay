# R overlay -- ebuild creation, ebuild construction
# -*- coding: utf-8 -*-
# Copyright (C) 2012 André Erdmann <dywi@mailerd.de>
# Distributed under the terms of the GNU General Public License;
# either version 2 of the License, or (at your option) any later version.

"""ebuild construction

This module provides one class, Ebuilder, that accepts evars and produces
an ebuild (as string).
"""

__all__ = [ 'Ebuilder', ]

class Ebuilder ( object ):
	"""Used to create ebuilds."""

	def __init__ ( self ):
		self._evars = list()
		# newlines \n will be inserted after an evar if the priority
		# delta (current evar, next evar) is >= this value.
		# <= 0 means newline after each statement
		self.min_newline_distance = 20

	def sort ( self ):
		"""Sorts the content of the Ebuilder."""
		self._evars.sort ( key=lambda e: ( e.priority, e.name ) )
		#self._evars.sort ( key=lambda e: e.priority )

	def get_lines ( self ):
		"""Creates and returns (ordered) text lines."""

		self.sort()
		last = len ( self._evars ) - 1

		newline = lambda i, k=1 : abs (
			self._evars [i + k].priority - self._evars [i].priority
		) >= self.min_newline_distance

		lines = list()
		for index, e in enumerate ( self._evars ):
			if e.active():
				varstr = str ( e )
				if varstr:
					lines.append ( str ( e ) )
					if index < last and newline ( index ): lines.append ( '' )

		return lines
	# --- end of get_lines (...) ---


	def to_str ( self ): return '\n'.join ( self.get_lines() )
	__str__ = to_str

	def use ( self, *evar_list ):
		"""Adds evars to this Ebuilder.

		arguments:
		* *evar_list --
		"""
		for e in evar_list:
			if e is not None: self._evars.append ( e )
