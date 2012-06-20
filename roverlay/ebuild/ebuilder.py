# R Overlay -- ebuild creation, <?>
# Copyright 2006-2012 Gentoo Foundation
# Distributed under the terms of the GNU General Public License v2

class Ebuilder ( object ):

	def __init__ ( self ):
		self._evars = list()

	def sort ( self ):
		self._evars.sort ( key=lambda e: e.priority )

	def get_lines ( self ):
		self.sort()
		last = len ( self._evars ) - 1

		newline = lambda i, k=1 : \
			abs ( self._evars [i + k].priority - self._evars [i].priority ) >= 20


		lines = list()
		for index, e in enumerate ( self._evars ):
			if e.active():
				lines.append ( str ( e ) )
				if index < last and newline ( index ): lines.append ( '' )

		return lines

	def to_str ( self ):
		return '\n'.join ( self.get_lines() )

	__str__ = to_str

	def use ( self, *evar_list ):
		for e in evar_list:
			self._evars.append ( e )
