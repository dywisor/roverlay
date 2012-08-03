# R Overlay -- ebuild creation, <?>
# -*- coding: utf-8 -*-
# Copyright 2006-2012 Gentoo Foundation
# Distributed under the terms of the GNU General Public License v2

import re

INDENT = '\t'

def listlike ( ref ):
	"""Returns True if ref is listlike (a non-str iterable)."""
	return hasattr ( ref, '__iter__' ) and not isinstance ( ref, str )


class ListValue ( object ):
	"""An evar value with a list of elements."""
	def __init__ ( self,
		value, indent_level=1, empty_value=None, bash_array=False
	):
		"""Initializes a ListValue.

		arguments:
		* value        --
		* indent_level -- indention level ('\t') for extra value lines
		* empty_value  -- if set: a string value that is always part
		                          of this ListValue's elements but ignored
		                          by len().
		                          Use cases are '${IUSE:-}' in the IUSE var etc.
		"""
		self.set_level ( indent_level )

		self.empty_value = empty_value


		self.single_line             = False
		self.indent_lines            = True
		# only used in multi line mode
		self.append_indented_newline = True

		self.is_bash_array           = bash_array
		self.insert_leading_newline  = self.is_bash_array

		self.val_join = ' '

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

	def set_level ( self, level ):
		"""Sets the indention level."""
		self.level      = level
		self.var_indent = (level - 1) * INDENT
		self.val_indent = level * INDENT
		self.line_join  = '\n' + self.val_indent
	# --- end of set_level (...) ---

	def set_value ( self, value ):
		"""Sets the value."""
		self.value = list()
		if self.empty_value is not None:
			self.value.append ( self.empty_value )

		if self._accept_value ( value ):
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

		value_count = len ( self.value )
		if self.is_bash_array:
			if value_count == 0:
				# empty value
				ret = "()"
			elif value_count == 1:
				# one value
				ret = "('" + str ( self.value [0] ) + "')"
			elif self.single_line:
				# several values in a single line
				ret = self.val_join.join ( self.value )
			else:
				ret = "{intro}{values}{tail}{newline}".format (
					intro   = '(\n' + self.val_indent \
						if self.insert_leading_newline else '( ',
					values  = self.line_join.join (
						"'" + str ( x ) + "'" for x in self.value
					),
					tail    = '\n{indent})'.format ( indent=self.var_indent ),
					newline = self.var_indent + '\n' \
						if self.append_indented_newline else ''
				)
		else:
			if value_count == 0:
				ret = ""
			elif value_count == 1:
				ret = str ( self.value [0] )
			else:
				if self.insert_leading_newline:
					ret  = '\n' + self.val_indent
					ret += self.line_join.join ( ( self.value ) )
				else:
					ret  = self.line_join.join ( ( self.value ) )

				if self.append_indented_newline:
					ret += self.var_indent + '\n'

		return ret
	# --- end of to_str (...) ---

	__str__ = to_str


class EbuildVar ( object ):
	"""An ebuild variable."""

	IGNORED_VALUE_CHARS = re.compile ( "[\"'`¸]" )

	def __init__ ( self, name, value, priority, param_expansion=True ):
		"""Initializes an EbuildVar.

		arguments:
		* name     -- e.g. 'SRC_URI'
		* value    --
		* priority -- used for sorting (e.g. 'R_SUGGESTS' before 'DEPEND'),
		               lower means higher priority
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

	def _quote_value ( self ):
		if hasattr ( self, '_get_value_str' ):
			vstr = self._get_value_str()
		else:
			vstr = str ( self.value )

		if self.use_param_expansion is None:
			# value quoting / unquoting is disabled
			return vstr

		else:
			q = '"' if self.use_param_expansion else '"'
			# removing all quote chars from values,
			#  the "constructed" {R,}DEPEND/R_SUGGESTS/IUSE vars don't use them
			#  and DESCRIPTION/SRC_URI don't need them
			if len ( vstr ) == 0:
				return 2 * q
			else:
				return q + EbuildVar.IGNORED_VALUE_CHARS.sub ( '', vstr ) + q
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
