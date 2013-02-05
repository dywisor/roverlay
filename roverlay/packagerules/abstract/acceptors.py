# R overlay -- abstract package rules, acceptors
# -*- coding: utf-8 -*-
# Copyright (C) 2013 André Erdmann <dywi@mailerd.de>
# Distributed under the terms of the GNU General Public License;
# either version 2 of the License, or (at your option) any later version.

"""
Classes provided by this module:
* Acceptor           -- base class for all acceptors
* ValueMatchAcceptor -- base class for acceptors that compare a value
* _AcceptorCompound  -- base class combines one more more acceptors
                         and represents a boolean term
                         IOW, they realize a function "[Acceptor] -> Bool"
* Acceptor_<type>    -- specific _AcceptorCompound classes
-> Acceptor_AND
-> Acceptor_OR
-> Acceptor_XOR1
-> Acceptor_NOR

Note:
	There's no Acceptor_NOT class.
	How would you define a multi-input function "not :: [Acceptor] -> Bool"?
	In most cases, you want "none of the listed Acceptors should match",
	which is exactly the definition of Acceptor_NOR.
"""

import roverlay.util

__all__ = [
	'Acceptor', 'ValueMatchAcceptor',
	'Acceptor_AND', 'Acceptor_OR', 'Acceptor_XOR1', 'Acceptor_NOR',
]

class EmptyAcceptorError ( ValueError ):
	"""
	Exception for "empty" Acceptors (Acceptor represents a boolean
	expression, but has no Acceptors attached).
	"""
	pass
# --- end of EmptyAcceptorError ---


class Acceptor ( object ):
	"""An Acceptor is able to determine whether it matches a PackageInfo
	instance or not.
	"""

	def __init__ ( self, priority ):
		super ( Acceptor, self ).__init__()
		self.priority = priority
		self.logger   = None
	# --- end of __init__ (...) ---

	def set_logger ( self, logger ):
		self.logger = logger.getChild ( self.__class__.__name__ )
	# --- end of logger (...) ---

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

	def _get_gen_str_indent ( self, level, match_level ):
		"""Returns the common prefix used in gen_str().

		arguments:
		* level
		* match_level
		"""
		if match_level > 1:
			return ( level * '   ' + ( match_level - 1 ) * '*' + ' ' )
		else:
			return level * '   '
	# --- end of _get_gen_str_indent (...) ---

	def gen_str ( self, level, match_level ):
		"""Yields text lines (str) that represent this match statement in
		text file format.

		arguments:
		* level       -- indention level
		* match_level -- match statement level
		"""
		raise NotImplementedError()
	# --- end of gen_str (...) ---

# --- end of Acceptor ---


class _AcceptorCompound ( Acceptor ):
	"""The base class for Acceptors that represent a boolean expression."""

	def __init__ ( self, priority ):
		super ( _AcceptorCompound, self ).__init__ ( priority )
		self._acceptors = list()
	# --- end of __init__ (...) ---

	def set_logger ( self, logger ):
		super ( _AcceptorCompound, self ).set_logger ( logger )
		for acceptor in self._acceptors:
			acceptor.set_logger ( self.logger )
	# --- end of set_logger (...) ---

	def prepare ( self ):
		"""Prepare the Acceptor for usage (typically used after loading
		it from a file).

		Sorts all Acceptors according to their priority.

		Raises: EmptyAcceptorError
		"""
		if len ( self._acceptors ) > 0:
			self._acceptors = roverlay.util.priosort ( self._acceptors )
			for acceptor in self._acceptors:
				acceptor.prepare()
		else:
			raise EmptyAcceptorError()
	# --- end of prepare (...) ---

	def add_acceptor ( self, acceptor ):
		"""Adds an Acceptor.

		arguments:
		* acceptor --
		"""
		self._acceptors.append ( acceptor )
	# --- end of add_acceptor (...) ---

	def gen_str ( self, level, match_level ):
		if match_level > 0:
			yield (
				self._get_gen_str_indent ( level, match_level )
				+ self.__class__.__name__[9:].lower()
			)

			for acceptor in self._acceptors:
				for s in acceptor.gen_str (
					level=( level + 1 ), match_level=( match_level + 1 )
				):
					yield s
		else:
			# top-level match block
			# * do not print "and"/"or"/...
			# * do not increase indent level

			for acceptor in self._acceptors:
				for s in acceptor.gen_str (
					level=level, match_level=( match_level + 1 )
				):
					yield s
	# --- end of gen_str (...) ---

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


class ValueMatchAcceptor ( Acceptor ):
	"""
	Base class for Acceptors that accept PackageInfo instances with a certain
	value (e.g. repo name, package name).
	"""

	def __init__ ( self, priority, get_value ):
		"""Constructor for ValueMatchAcceptor.

		arguments:
		* priority  -- priority of this Acceptor
		* get_value -- function F(<PackageInfo>) that is used to get the
		               value
		"""
		super ( ValueMatchAcceptor, self ).__init__ ( priority=priority )
		self._get_value = get_value
	# --- end of __init__ (...) ---

	def _matches ( self, value ):
		"""Returns true if this acceptor matches the given value.

		arguments:
		* value --
		"""
		raise NotImplementedError()
	# --- end of _matches (...) ---

	def accepts ( self, p_info ):
		compare_to = self._get_value ( p_info )
		if self._matches ( compare_to ):
			self.logger.debug ( "accepts {}".format ( compare_to ) )
			return True
		else:
			return False
	# --- end of accepts (...) ---

	def _get_value_name ( self ):
		"""Returns the name that describes the value which this acceptor is
		comparing to, e.g. "repo_name" or "package".

		Meant for usage in gen_str().
		"""
		if hasattr ( self._get_value, 'func_name' ):
			n = self._get_value.func_name
		elif hasattr ( self._get_value, '__name__' ):
			n = self._get_value.__name__
		else:
			return str ( self._get_value )

		if n[:4] == 'get_':
			return n[4:] or n
		else:
			return n
	# --- end of _get_value_name (...) ---

# --- end of ValueMatchAcceptor ---
