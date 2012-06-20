# R Overlay -- ebuild creation, <?>
# Copyright 2006-2012 Gentoo Foundation
# Distributed under the terms of the GNU General Public License v2

INDENT = '\t'

def listlike ( ref ):
	return hasattr ( ref, '__iter__' ) and not isinstance ( ref, str )


class ListValue ( object ):
	def __init__ ( self, value, indent_level=1, empty_value=None ):
		self.set_level ( indent_level )

		self.empty_value = empty_value


		self.single_line             = False
		self.indent_lines            = True
		# only used in multi line mode
		self.append_indented_newline = True

		self.val_join = ' '

		self.set_value ( value )


	def __len__ ( self ):
		l = len ( self.value )
		return l if self.empty_value is None else l - 1

	def set_level ( self, level ):
		self.level      = level
		self.var_indent = (level - 1) * INDENT
		self.val_indent = level * INDENT
		self.line_join  = '\n' + self.val_indent
	# --- end of set_level (...) ---

	def set_value ( self, value ):
		self.value = list()
		if self.empty_value is not None:
			self.value.append ( self.empty_value )
		self.add_value ( value )
	# --- end of set_value (...) ---

	def add_value ( self, value ):
		if value is None:
			pass
		elif listlike ( value ):
			self.value.extend ( value )
		else:
			self.value.append ( value )
	# --- end of add_value (...) ---

	add = add_value

	def to_str ( self ):
		if len ( self.value ) == 0:
			ret = ""
		elif len ( self.value ) == 1:
			ret = str ( self.value [0] )
		elif self.single_line:
			ret = self.val_join.join ( self.value )
		else:
			ret = self.line_join.join ( ( self.value ) )
			if self.append_indented_newline:
				ret += self.var_indent + '\n'

		return ret
	# --- end of to_str (...) ---

	__str__ = to_str


class EbuildVar ( object ):

	def __init__ ( self, name, value, priority ):
		self.name     = name
		self.priority = priority
		self.value    = value
		self.set_level ( 0 )

	def set_level ( self, level ):
		self.level  = level
		self.indent = self.level * INDENT
		if hasattr ( self.value, 'set_level' ):
			self.value.set_level ( level + 1 )
	# --- end of set_level (...) ---

	def active ( self ): return True

	def __str__ ( self ):
		return '%s%s="%s"' % ( self.indent, self.name, self.value )
