# R Overlay -- ebuild creation, ebuild class
# Copyright 2006-2012 Gentoo Foundation
# Distributed under the terms of the GNU General Public License v2

class Ebuild ( object ):

	def __init__ ( self, content, header=None ):
		"""Initializes an Ebuild that has text content and optionally a
		header (text, too).

		arguments:
		* content --
		* header  --
		"""
		self.content = content
		self.header  = header
	# --- end of __init__ (...) ---

	def write ( self, fh, header=None, header_is_fallback=False ):
		"""Write the ebuild into a file-like object.

		arguments:
		* fh -- file handle
		"""
		if not self.content:
			raise Exception ( "ebuild is empty!" )

		header_order = ( self.header, header ) if header_is_fallback \
								else ( header, self.header )

		for h in header_order:
			if not h is None:
				fh.write ( h )
				fh.write ( '\n\n' )
				break

		fh.write ( self.content )
		fh.write ( '\n' )
	# --- end of write_fh (...) ---
