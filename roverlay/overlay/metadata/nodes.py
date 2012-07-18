# R Overlay -- ebuild creation, concrete metadata nodes
# Copyright 2006-2012 Gentoo Foundation
# Distributed under the terms of the GNU General Public License v2

from roverlay import util
# import abstract nodes
from roverlay.overlay.metadata.abstractnodes import \
	MetadataNode, MetadataNodeNamedAccess, MetadataLeaf


class MetadataRoot ( MetadataNodeNamedAccess ):
	"""This is the metadata root which represents a metadata file.
	Intended usage is metadata file creation.
	"""

	# the common metadata.xml header
	HEADER = '\n'.join ( [
		'<?xml version="1.0" encoding="UTF-8"?>',
		'<!DOCTYPE pkgmetadata SYSTEM "http://www.gentoo.org/dtd/metadata.dtd">'
	] )


	def __init__ ( self ):
		super ( MetadataRoot, self ) . __init__ ( 'pkgmetadata' )
		self.priority = 0
	# --- end of __init__ (...) ---

	def empty ( self ):
		"""Returns True if this node has no child nodes."""
		#return 0 == len ( self.nodes ) or \
		#	True in ( node.empty() for node in self.nodes )
		return 0 == len ( self.nodes )
	# --- end of empty (...) ---

	def add_useflag ( self, flag_name, flag_description ):
		"""Adds a USE Flag to the metadata.
		A UseFlagListNode 'use' will be created if required and a new UseFlagNode
		will then be created an added to 'use'.

		arguments:
		* flag_name        -- see UseFlagNode.__init__
		* flag_description -- see UseFlagNode.__init__

		returns: the created UseFlagNode for further editing
		"""
		if not self.has_named ( 'use' ):
			# passing fail_if_existent, this node shouldn't be used in parallel
			self.add (
				UseFlagListNode(),
				with_dict_entry=True, fail_if_existent=True
			)

		node = self.get ( 'use' )
		use_node = UseFlagNode ( flag_name, flag_description )
		node.add ( use_node )

		return use_node
	# --- end of add_useflag (...) ---

	def write_file ( self, _file ):
		"""Writes the metadata to a file.

		arguments:
		* _file -- either a File object or a string

		returns: success True/False

		raises: *passes IOError
		"""
		to_write = util.ascii_filter ( self.to_str() )

		own_fh  = False
		fh      = None
		success = False

		newline = '\n'

		try:
			if isinstance ( _file, str ):
				own_fh = True
				fh     = open ( _file, 'w' )
			else:
				fh     = _file


			fh.write ( MetadataRoot.HEADER )
			fh.write ( newline )
			fh.write ( to_write )
			fh.write ( newline )

			success = True

		except IOError:
			# log this TODO
			pass
		finally:
			if own_fh and fh: fh.close()

		return success
	# --- end of write_file (...) ---


class DescriptionNode ( MetadataLeaf ):
	"""A description (<longdescription.../>) node."""

	def __init__ ( self, description, linewidth=None ):
		"""Initializes a DescriptionNode.

		arguments:
		* description -- description text
		* linewidth   -- max text line width
		"""
		super ( DescriptionNode, self ) . __init__ (
			'longdescription', value=description
		)

		if not linewidth is None and linewidth > 0:
			self.linewidth = linewidth

		self.priority = 150
	# --- end of __init__ (...) ---

	# using value formatting
	_value_str = MetadataLeaf._pretty_value_str


class UseFlagNode ( MetadataLeaf ):
	"""A USE Flag node, <flag name=x>this flag does...</flag>"""
	def __init__ ( self, flag_name, flag_description ):
		"""Initializes an USE Flag node.

		arguments:
		* flag_name        -- name of the use flag
		* flag_description -- flag description
		"""
		super ( UseFlagNode, self ) . __init__ (
			'flag',
			flags=dict ( name = flag_name ),
			value=flag_description,
		)
		# priority shouldn't be used for this node
		self.priority = -1
	# --- end of __init__ (...) ---


class UseFlagListNode ( MetadataNode ):
	"""A USE Flag list node, <use>...</use>."""

	def __init__ ( self, flags=dict() ):
		"""Initializes an USE Flag list node.

		arguments:
		* flags -- optional
		"""
		super ( UseFlagListNode, self ) . __init__ ( 'use', flags=flags )
		self.priority = 850
	# --- end of __init__ (...) ---

	def active ( self ):
		"""The UseFlag list is only active if it is enabled and at least
		one UseFlag child node is active.
		"""
		# generator should stop after first True
		return self._enabled and \
			True in ( node.active() for node in self.nodes )
	# --- end of active (...) ---

	def _sort_nodes ( self ):
		"""UseFlags are sorted by lowercase flag name, not priority."""
		self.nodes.sort ( key=lambda node : node.flags ['name'].lower() )
	# --- end of _sort_nodes (...) ---

	def add ( self, node ):
		"""Adds a child node only if it is a UseFlagNode.

		arguments:
		* node --
		"""
		if isinstance ( node, UseFlagNode ):
			super ( UseFlagListNode, self ) . add ( node )
		else:
			raise Exception ( "UseFlagListNode accepts UseFlagNodes only." )
	# --- end of add (...) ---


class NopNode ( MetadataNode ):
	"""This node is meant for testing only."""
	def __init__ ( self ):
		super ( NopNode, self ) . __init__ ( 'nop', flags=dict() )
	# --- end of __init__ (...) ---
