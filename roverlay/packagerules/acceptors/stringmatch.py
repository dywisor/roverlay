# R overlay -- package rules, value/string acceptors
# -*- coding: utf-8 -*-
# Copyright (C) 2013 André Erdmann <dywi@mailerd.de>
# Distributed under the terms of the GNU General Public License;
# either version 2 of the License, or (at your option) any later version.

import re

import roverlay.packagerules.abstract.acceptors

class ValueAcceptor (
	roverlay.packagerules.abstract.acceptors.ValueMatchAcceptor
):
	"""Exact value match Acceptor."""

	def __init__ ( self, priority, get_value, value ):
		"""Constructor for ValueAcceptor.

		arguments:
		* priority  -- priority of this Acceptor
		* get_value -- function that returns a value
		* _str      -- string that should match that^ value
		"""
		super ( ValueAcceptor, self ).__init__ (
			priority  = priority,
			get_value = get_value
		)
		self._value = value
	# --- end of __init__ (...) ---

	def _matches ( self, value ):
		return self._value == value
	# --- end of _matches (...) ---

	def gen_str ( self, level, match_level ):
		yield (
			self._get_gen_str_indent ( level, match_level )
			+ self._get_value_name() + ' == ' + str ( self._value )
		)
	# --- end of gen_str (...) ---

# --- end of ValueAcceptor ---


class StringAcceptor ( ValueAcceptor ):
	"""Exact string match Acceptor."""
	pass

# --- end of StringAcceptor ---


class NocaseStringAcceptor ( StringAcceptor ):
	"""Case-insensitive string match Acceptor."""

	def __init__ ( self, priority, get_value, _str ):
		super ( NocaseStringAcceptor, self ).__init__ (
			priority  = priority,
			get_value = get_value,
			value     = _str.lower()
		)
	# --- end of __init__ (...) ---

	def _matches ( self, value ):
		return self._value == value.lower()
	# --- end of _matches (...) ---

	def gen_str ( self, level, match_level ):
		yield (
			self._get_gen_str_indent ( level, match_level )
			+ self._get_value_name() + ' ,= ' + self._value
		)
	# --- end of gen_str (...) ---

# --- end of NocaseStringAcceptor ---


class RegexAcceptor (
	roverlay.packagerules.abstract.acceptors.ValueMatchAcceptor
):
	"""Regex match Acceptor."""

	def __init__ ( self, priority, get_value, regex=None, regex_compiled=None ):
		"""Constructor for RegexAcceptor.

		arguments:
		* priority       -- see _ValueMatchAcceptor
		* get_value      -- see _ValueMatchAcceptor
		* regex          -- a regex string
		* regex_compiled -- a compiled regex

		Either regex or regex_compiled must be specified, else an exception
		is raised.
		"""
		super ( RegexAcceptor, self ).__init__ (
			priority  = priority,
			get_value = get_value
		)

		# exactly-one-of (regex, regex_compiled)
		if bool ( regex ) == bool ( regex_compiled ):
			raise Exception (
				"either 'regex' or 'regex_compiled' must be passed to {}".format (
					self.__class__.__name__
				)
			)

		self._regex = regex_compiled if regex_compiled else re.compile ( regex )
	# --- end of __init__ (...) ---

	def _matches ( self, value ):
		return bool ( self._regex.search ( value ) )
	# --- end of _matches (...) ---

	def gen_str ( self, level, match_level ):
		yield (
			self._get_gen_str_indent ( level, match_level )
			+ self._get_value_name() + ' ~ ' + self._regex.pattern
		)
	# --- end of gen_str (...) ---

# --- end of RegexAcceptor ---


class ExactRegexAcceptor ( RegexAcceptor ):
	"""Exact regex match Acceptor (matches "^<regex>$")."""

	def __init__ ( self, priority, get_value, regex ):
		super ( ExactRegexAcceptor, self ).__init__ (
			priority  = priority,
			get_value = get_value,
			regex      = '^' + regex + '$'
		)
	# --- end of __init__ (...) ---

	def _matches ( self, value ):
		# using re.match instead of re.search
		return bool ( self._regex.match ( value ) )
	# --- end of _matches (...) ---

	def gen_str ( self, level, match_level ):
		yield (
			self._get_gen_str_indent ( level, match_level )
			+ self._get_value_name() + ' ~= ' + self._regex.pattern
		)
	# --- end of gen_str (...) ---

# --- end of ExactRegexAcceptor ---
