# R overlay -- ebuild creation, ebuild variables (abstract)
# -*- coding: utf-8 -*-
# Copyright (C) 2012 André Erdmann <dywi@mailerd.de>
# Distributed under the terms of the GNU General Public License;
# either version 2 of the License, or (at your option) any later version.

"""abstract ebuild variables

This module defines two classes:
* EbuildVar -- the base class for ebuild variables (e.g. IUSE="...")
* ListValue -- an object that stores multiple values in an EbuildVar-usable
               format.
               For example, it supports "empty values" (RDEPEND="${DEPEND:-}")
               and bash array string representations ("array=('a' 'b')").
"""

__all__ = [ 'ListValue', 'EbuildVar', ]

import re

import roverlay.strutil

INDENT = '\t'

# IGNORED_VALUE_CHARS
#  chars not allowed in value strings
#  Additionally, backslashes at the end of a string will be removed.
IGNORED_VALUE_CHARS  = "\"'`;"

def _value_char_allowed ( c ):
	"""Returns True if the given char is allowed, else False (=char should
	be ignored.

	arguments:
	* c --
	"""
	return c not in IGNORED_VALUE_CHARS
# --- end of _value_char_allowed (...) ---

## IGNORED_VALUE_CODE, catches:
## * command substitution: $(<cmd>), $(< <file>)
## * arithmetic expansion: $((<statement>))
##
#IGNORED_VALUE_CODE = re.compile (
#	'[$][(]{1,2}[<]?(?P<text>.*?)[)]{1,2}\s*'
#)

# IGNORED_VALUE_CODE (strict), catches:
# * any (sub)string beginning with '$(' which is either not allowed
#   or it leads to syntax errors
#
# This will remove more text than the variant above, but we cannot trust
# that code injection always uses correct syntax.
#
IGNORED_VALUE_CODE = re.compile ( '[$][(].*' )

def get_value_str ( value, quote_char=None ):
	"""Removes bad chars / substrings from vstr:
	* non-ascii chars (this could be a no-op)
	* IGNORED_VALUE_CHARS
	* any substring starting with $(
	* backslash characters at the end of the string

	arguments:
	* value --
	"""
	s = IGNORED_VALUE_CODE.sub (
		"",
		roverlay.strutil.ascii_filter (
			str ( value ), additional_filter=_value_char_allowed
		)
	).rstrip ( "\\" )
	if quote_char:
		return quote_char + s + quote_char
	else:
		return s
# --- end of get_value_str (...) ---

def listlike ( ref ):
	"""Returns True if ref is listlike (a non-str iterable)."""
	return hasattr ( ref, '__iter__' ) and not isinstance ( ref, str )
# --- end of listlike (...) ---


class ListValue ( object ):
	"""An evar value with a list of elements."""
	def __init__ ( self,
		value, indent_level=1, empty_value=None, bash_array=False
	):
		"""Initializes a ListValue.

		arguments:
		* value        --
		* indent_level -- indention level ('\t') for value string lines
		* empty_value  -- if set: a string value that is always part
		                   of this ListValue's elements but ignored when
		                   checking the number of stored items.
		                   Use cases are '${IUSE:-}' in the IUSE var etc.
		                   Defaults to None (which disables this feature).
		* bash_array   -- whether this value is a bash array or a string
		                   Defaults to False.
		"""
		self.empty_value             = empty_value
		self.single_line             = False
		self.indent_lines            = True
		self.is_bash_array           = bash_array
		self.insert_leading_newline  = self.is_bash_array

		# only used when dealing with multi-line non-bash array values:
		#  append \n<var_indent> to the value string if True (useful for quoting
		#  such strings)
		self.append_indented_newline = True

		self.set_level ( indent_level )
		self.set_value ( value )
	# --- end of __init__ (...) ---

	def _accept_value ( self, value ):
		if value is None:
			return False
		# "not str or len > 0" will raise exceptions for integers etc.
		elif isinstance ( value, str ) and len ( value ) == 0:
			return False
		else:
			return True
	# --- end _accept_value (...) ---

	def __len__ ( self ):
		l = len ( self.value )
		return max ( 0, l if self.empty_value is None else l - 1 )
	# --- end of __len__ (...) ---

	def set_level ( self, level ):
		"""Sets the indention level."""
		self.level         = level
		self.var_indent    = (level - 1) * INDENT
		self.val_indent    = level * INDENT
		self.line_join_str = '\n' + self.val_indent
	# --- end of set_level (...) ---

	def set_value ( self, value ):
		"""Sets the value."""
		self.value = list()
		if self.empty_value is not None:
			self.value.append ( self.empty_value )

		self.add_value ( value )
	# --- end of set_value (...) ---

	def add ( self, value ):
		"""Adds/Appends a value."""
		if not self._accept_value ( value ):
			pass
		elif listlike ( value ):
			self.value.extend ( value )
		else:
			self.value.append ( value )
	# --- end of add (...) ---

	add_value = add

	def to_str ( self ):
		"""Returns a string representing this ListValue."""

		def get_value_strings ( join_str, quoted=False ):
			return join_str.join (
				get_value_str (
					v,
					quote_char = "'" if quoted else None
				) for v in self.value
			)
		# --- end of get_value_strings (...) ---

		value_count = len ( self.value )

		if self.is_bash_array:
			if value_count == 0:
				# empty value
				ret = "()"

			elif self.single_line or value_count == 1:
				# one value or several values in a single line
				ret = "( " + get_value_strings ( ' ', True ) + " )"

			else:
				ret = "{head}{values}{tail}".format (
					head   = (
						( '(\n' + self.val_indent )
						if self.insert_leading_newline else '( '
					),
					values = get_value_strings ( self.line_join_str, True ),
					tail   = '\n' + self.var_indent + ')\n'
				)
		else:
			if value_count == 0:
				ret = ""
			elif self.single_line or value_count == 1:
				ret = get_value_strings ( ' ' )
			else:
				if self.insert_leading_newline:
					ret  = '\n' + self.val_indent
					ret += get_value_strings ( self.line_join_str )
				else:
					ret  = get_value_strings ( self.line_join_str )

				if self.append_indented_newline:
					ret += '\n' + self.var_indent

		return ret
	# --- end of to_str (...) ---

	__str__ = to_str

# --- end of ListValue ---


class EbuildVar ( object ):
	"""An ebuild variable."""

	def __init__ ( self, name, value, priority, param_expansion=True ):
		"""Initializes an EbuildVar.

		arguments:
		* name            -- e.g. 'SRC_URI'
		* value           --
		* priority        -- used for sorting (e.g. 'R_SUGGESTS'
		                      before 'DEPEND'), lower means higher priority
		* param_expansion -- set the char that is used to quote the value
		                      True : "
		                      False: '
		                      None : use raw value string
		"""
		self.name                = name
		self.priority            = priority
		self.value               = value
		self.set_level ( 0 )
		self.use_param_expansion = param_expansion
		self.print_empty_var     = False

		if hasattr ( self.value, 'add' ):
			self.add_value = self.value.add
	# --- end of __init__ (...) ---

	def set_level ( self, level ):
		"""Sets the indention level."""
		self.level  = level
		self.indent = self.level * INDENT
		if hasattr ( self.value, 'set_level' ):
			self.value.set_level ( level + 1 )
	# --- end of set_level (...) ---

	def active ( self ):
		"""Returns True if this EbuildVar is enabled and has a string to
		return.
		(EbuildVar's active() returns always True, derived classes may
		override this.)
		"""
		if hasattr ( self, 'enabled' ):
			return self.enabled
		elif hasattr ( self.value, '__len__' ):
			return len ( self.value ) > 0
		else:
			return True
	# --- end of active (...) ---

	def _get_value_str ( self ):
		# hasattr ( ?? )
		if isinstance ( self.value, ListValue ):
			return self.value.to_str()
		else:
			return get_value_str ( self.value )
	# --- end of _get_value_str (...) ---

	def _quote_value ( self ):
		vstr = self._get_value_str()

		if hasattr ( self, '_transform_value_str' ):
			vstr = self._transform_value_str ( vstr )
		# -- end if

		if self.use_param_expansion is None:
			# value quoting / unquoting is disabled
			return vstr

		else:
			q = '"' if self.use_param_expansion else "'"
			# removing all quote chars from values,
			#  the "constructed" {R,}DEPEND/R_SUGGESTS/IUSE vars don't use them
			#  and DESCRIPTION/SRC_URI don't need them
			if len ( vstr ) == 0:
				return 2 * q
			else:
				return q + vstr + q
	# --- end of _quote_value (...) ---

	def __str__ ( self ):
		valstr = self._quote_value()
		if len ( valstr ) >  2 or self.print_empty_var:
			return "{indent}{name}={value}".format (
				indent=self.indent, name=self.name, value=valstr
			)
		else:
			# empty string 'cause var is not set
			#  -> Ebuilder ignores this var
			# this filters out the result of strip(QUOTE_CHARS) for values that
			# contain only quote chars
			return self._empty_str() if hasattr ( self, '_empty_str' ) else ""
	# --- end of __str__ (...) ---

# --- end of EbuildVar ---
