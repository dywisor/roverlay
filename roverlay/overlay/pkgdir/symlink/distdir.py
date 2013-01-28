# R overlay -- overlay package, symlink distdir
# -*- coding: utf-8 -*-
# Copyright (C) 2013 André Erdmann <dywi@mailerd.de>
# Distributed under the terms of the GNU General Public License;
# either version 2 of the License, or (at your option) any later version.

import os

__all__ = [ 'SymlinkDistdir', ]

class SymlinkDistdir ( object ):

	def __init__ ( self, root ):
		"""Initializes a symlink DISTDIR.

		arguments:
		* root -- directory where symlinks will be created
		"""
		self.root = root
		if not os.path.isdir ( self.root ):
			os.mkdir ( self.root )
	# --- end of __init__ (...) ---

	def add ( self, fpath, fname=None ):
		"""Adds a symlink to a file to this dir.

		arguments:
		* fpath -- path to the file for which a symlink will be created
		* fname -- name of the symlink, defaults to os.path.basename ( fpath )
		"""
		symlink = self.root + os.sep + ( fname or os.path.basename ( fpath ) )

		if os.path.lexists ( symlink ):
			os.unlink ( symlink )

		if not os.path.exists ( symlink ):
			os.symlink ( fpath, symlink )
			return symlink
		else:
			raise OSError ( "cannot set up symlink {!r}!".format ( symlink ) )
	# --- end of add (...) ---

	def __str__ ( self ):
		return self.root
	# --- end of __str__ (...) ---

# --- end of SymlinkDistdir ---
