# R Overlay -- ebuild creation, concrete metadata nodes
# Copyright 2006-2012 Gentoo Foundation
# Distributed under the terms of the GNU General Public License v2

# -- concrete metadata nodes --

from roverlay.portage.metadata.abstractnodes import \
	MetadataNode, MetadataNodeNamedAccess, MetadataLeaf


class MetadataRoot ( MetadataNodeNamedAccess ):
	"""This is the metadata root which represents a metadata file.
	Intended usage is metadata file creation.
	"""

	HEADER = '\n'.join ( [
		'<?xml version="1.0" encoding="UTF-8"?>',
		'<!DOCTYPE pkgmetadata SYSTEM "http://www.gentoo.org/dtd/metadata.dtd">'
	] )

	def __init__ ( self ):
		super ( MetadataRoot, self ) . __init__ ( 'pkgmetadata' )
		self.priority = 0

	def empty ( self ):
		#return 0 == len ( self.nodes ) or \
		#	True in ( node.empty() for node in self.nodes )
		return 0 == len ( self.nodes )

	def write_file ( self, _file ):
		to_write = self.to_str()

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
	def __init__ ( self, description, is_long=False, linewidth=None ):
		super ( DescriptionNode, self ) . __init__ (
			'longdescription' if is_long else 'description',
			value=description,
		)
		# self.value_format = "break lines after 80c, ..."

		if not linewidth is None and linewidth > 0:
			self.linewidth = linewidth

		self.priority = 150 if is_long else 149

	_value_str = MetadataLeaf._pretty_value_str

class UseFlagNode ( MetadataLeaf ):
	def __init__ ( self, flag_name, flag_description ):
		super ( UseFlagNode, self ) . __init__ (
			'flag',
			flags=dict ( name = flag_name ),
			value=flag_description,
		)
		# priority shouldn't be used for this node
		self.priority = -1


class UseFlagListNode ( MetadataNode ):
	def __init__ ( self, flags=dict() ):
		super ( UseFlagListNode, self ) . __init__ ( 'use', flags=flags )
		self.priority = 850

	def active ( self ):
		"""The UseFlag list is only active if it is enabled and at least
		one UseFlag child node is active.
		"""
		# generator should stop after first True
		# todo/fixme: could use super ( UseFlagListNode, self ).active() instead
		# of self._enabled
		return True in ( node.active() for node in self.nodes ) and self._enabled


	def _sort_nodes ( self ):
		"""UseFlags are sorted by lowercase flag name, not priority."""
		self.nodes.sort ( key=lambda node : node.flags ['name'].lower() )

	def add ( self, node ):
		if isinstance ( node, UseFlagNode ):
			super ( UseFlagListNode, self ) . add ( node )
		else:
			raise Exception ( "UseFlagListNode accepts UseFlagNodes only." )




class NopNode ( MetadataNode ):
	def __init__ ( self ):
		super ( NopNode, self ) . __init__ ( 'nop', flags=dict() )
