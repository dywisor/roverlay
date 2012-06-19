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

	def write ( self, fh, header=None ):
		"""Write the ebuild into a file-like object.

		arguments:
		* fh -- file handle
		"""
		if not self.content:
			raise Exception ( "ebuild is empty!" )

		if header is None:
			if not self.header is None:
				fh.write ( self.header )
				fh.write ( '\n' )
		else:
			fh.write ( header )
			fh.write ( '\n' )

		fh.write ( self.content )
		fh.write ( '\n' )
	# --- end of write_fh (...) ---
