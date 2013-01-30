# R overlay -- abstract package rules, acceptors
# -*- coding: utf-8 -*-
# Copyright (C) 2013 André Erdmann <dywi@mailerd.de>
# Distributed under the terms of the GNU General Public License;
# either version 2 of the License, or (at your option) any later version.

import roverlay.util

__all__ = [
	'Acceptor',
	'Acceptor_AND', 'Acceptor_OR', 'Acceptor_XOR1', 'Acceptor_NOR',
]

class EmptyAcceptor ( ValueError ):
	"""
	Exception for "empty" Acceptors (Acceptor represents a boolean
	expression, but has no Acceptors attached).
	"""
	pass
# --- end of EmptyAcceptor ---


class Acceptor ( object ):
	"""An Acceptor is able to determine whether it matches a PackageInfo
	instance or not.
	"""

	def __init__ ( self, priority ):
		super ( Acceptor, self ).__init__()
		self.priority = priority
	# --- end of __init__ (...) ---

	def prepare ( self ):
		"""Prepare the Acceptor for usage (typically used after loading
		it from a file).
		"""
		pass
	# --- end of prepare (...) ---

	def accepts ( self, p_info ):
		"""Returns True if this Acceptor matches the given PackageInfo, else
		False.

		arguments:
		* p_info --
		"""
		raise NotImplementedError()
	# --- end of accepts (...) ---

# --- end of Acceptor ---

class _AcceptorCompound ( Acceptor ):
	"""The base class for Acceptors that represent a boolean expression."""

	def __init__ ( self, priority ):
		super ( _AcceptorCompound, self ).__init__ ( priority )
		self._acceptors = list()
	# --- end of __init__ (...) ---

	def prepare ( self ):
		"""Prepare the Acceptor for usage (typically used after loading
		it from a file).

		Sorts all Acceptors according to their priority.

		Raises: EmptyAcceptor
		"""
		if len ( self._acceptors ) > 0:
			self._acceptors = roverlay.util.priosort ( self._acceptors )
			for acceptor in self._acceptors:
				acceptor.prepare()
		else:
			raise EmptyAcceptor()
	# --- end of prepare (...) ---

	def add_acceptor ( self, acceptor ):
		"""Adds an Acceptor.

		arguments:
		* acceptor --
		"""
		self._acceptors.append ( acceptor )
	# --- end of add_acceptor (...) ---

# --- end of _AcceptorCompound ---

class Acceptor_OR ( _AcceptorCompound ):
	"""OR( <Acceptors> )"""

	def accepts ( self, p_info ):
		"""Returns True if any attached Acceptor returns True, else False.

		arguments:
		* p_info --
		"""
		for acceptor in self._acceptors:
			if acceptor.accepts ( p_info ):
				return True
		return False
	# --- end of accepts (...) ---

# --- end of Acceptor_OR ---

class Acceptor_AND ( _AcceptorCompound ):
	"""AND( <Acceptors> )"""

	def accepts ( self, p_info ):
		"""Returns True if all acceptors accept p_info, else False.

		arguments:
		* p_info --
		"""
		for acceptor in self._acceptors:
			if not acceptor.accepts ( p_info ):
				return False
		return True
	# --- end of accepts (...) ---

# --- end of Acceptor_AND ---

class Acceptor_XOR1 ( _AcceptorCompound ):
	"""XOR( <Acceptors> )"""

	# XOR  := odd number of matches
	# XOR1 := exactly one match

	def accepts ( self, p_info ):
		"""Returns True if exactly one acceptor accepts p_info, else False.

		arguments:
		* p_info --
		"""
		any_true = False
		for acceptor in self._acceptors:
			if acceptor.accepts ( p_info ):
				if any_true:
					return False
				else:
					any_true = True
		return any_true
	# --- end of accepts (...) ---

# --- end of Acceptor_XOR1 ---

class Acceptor_NOR ( Acceptor_OR ):
	"""NOR( <Acceptors> )"""

	def accepts ( self, p_info ):
		"""Returns True if no acceptor accepts p_info, else False.

		arguments:
		* p_info --
		"""
		return not super ( Acceptor_NOR, self ).accepts ( p_info )
	# --- end of accepts (...) ---

# --- end of Acceptor_NOR ---
