# R Overlay -- ebuild creation, basic metadata nodes
# Copyright 2006-2012 Gentoo Foundation
# Distributed under the terms of the GNU General Public License v2


# -- "abstract" metadata nodes --
class _MetadataBasicNode ( object ):
	INDENT = '\t'

	def __init__ ( self, name, flags ):
		self.name     = name
		self.flags    = flags
		self.priority = 1000
		self._set_level ( 0 )
	# --- end of __init__ (...) ---

	def _set_level ( self, _level, has_indent=True ):
		self.level = _level
		if has_indent:
			self.indent = self.level * _MetadataBasicNode.INDENT
		else:
			self.indent = ''
	# --- end of _set_level (...) ---

	def set_flag ( self, flagname, flagvalue=None ):
		self.flags [flagname] = '' if flagvalue is None else flagvalue
	# --- end of set_flag (...) ---

	def _flaglist ( self, flag_dict ):
			return [ '%s="%s"' % ftup for ftup in self.flags.items() ]
	# --- end of _flaglist (...) ---

	def _flagstr ( self ):
		if self.flags is None:
			return ''

		ret = ' '.join ( _flaglist )
		if ret:
			# don't forget the leading space
			return ' ' + ret
		else:
			return ''
	# --- end of _flagstr (...) ---

	def _do_verify ( self ):
		if hasattr ( self, '_verify' ) and not self._verify():
			# todo, verify could return ( Status, ErrorMessages ) etc.
			raise Exception ( "verification failed for a metadata node." )

	# not using __repr__, make (recursive) node calls explicit
	def to_str ( self ):
		self._do_verify()

		return "%s<%s%s></%s>" % (
			self.indent,
			self.name,
			self._flagstr(),
			self.name
		)


class MetadataNode ( _MetadataBasicNode ):

	def __init__ ( self, name, flags=dict() ):
		super ( MetadataNode, self ) . __init__ ( name, flags )
		self.nodes = list()
	# --- end of __init__ (...) ---

	def add ( self, node ):
		node._set_level ( self.level + 1 )
		self.nodes.append ( node )

	_add_node = add

	def _sort_nodes ( self ):
		self.nodes.sort ( lambda node : node.priority )

	def _nodelist ( self ):
		return list (
			filter (
				None,
				[ node.to_str() for node in self.nodes ]
			),
		)
	# --- end of _nodelist (...) ---

	def _nodestr ( self ):
		self._sort_nodes()
		# todo filter only None?
		node_repr = self._nodelist()
		if len ( node_repr ):
			return "\n%s\n%s" % ( '\n'.join ( node_repr ), self.indent )
		else:
			return ''
	# --- end of _nodestr (...) ---

	def to_str ( self ):
		self._do_verify()
		return "%s<%s%s>%s</%s>" % (
			self.indent,
			self.name,
			self._flagstr(),
			self._nodestr(),
			self.name
		)


class MetadataNodeOrdered ( MetadataNode ):
	"""A metadata node whose nodes have to be interpreted as an already
	ordered string."""
	# could derive MetadataNode from this
	def _sort_nodes ( self ): return


class MetadataLeaf ( _MetadataBasicNode ):
	"""A metadata node that has no child nodes, only a string."""

	def __init__ ( self, name, flags=dict(), value=None ):
		super ( MetadataLeaf, self ) . __init__ ( name, flags )
		self.value             = "" if value is None else value
		self.print_node_name   = True
		self.value_format      = 0

	def _value_str ( self ):
		#if self.value_format == ?: format value ~
		return self.value

	def to_str ( self ):
		self._do_verify()
		if self.print_node_name:
			return "%s<%s%s>%s</%s>" % (
				self.indent,
				self.name,
				self._flagstr(),
				self._value_str(),
				self.name
			)
		else:
			# not very useful, but allows to insert strings as nodes
			return self.indent + self._value_str()


class MetadataNodeNamedAccess ( MetadataNode ):
	"""A metadata node that offers key-based (dictionary) access to some of
	its nodes."""

	def __init__ ( self, name, flags=dict() ):
		super ( MetadataNodeNamedAccess, self ) . __init__ ( name, flags )
		self.node_dict = dict()

	def add ( self, node, with_dict_entry=True, fail_if_existent=True ):
		"""comment TODO; overwrites old dict entries!"""
		super ( MetadataNodeNamedAccess, self ) . add ( node )
		if with_dict_entry:
			if fail_if_existent and node.name in self.node_dict:
				raise Exception ( "key exists." )
			else:
				self.node_dict [node.name] = node

	def get_node ( self, node_name ):
		return self.node_dict [node_name]
