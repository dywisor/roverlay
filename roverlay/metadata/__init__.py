# R Overlay -- ebuild creation, metadata creation
# Copyright 2006-2012 Gentoo Foundation
# Distributed under the terms of the GNU General Public License v2

import roverlay.config

from roverlay.metadata import nodes

USE_FULL_DESCRIPTION = True

class MetadataJob ( object ):
	"""R package description data -> metadata.xml interface."""

	def __init__ ( self, logger ):
		"""Initializes a MetadataJob.

		arguments:
		* logger       -- parent logger to use
		"""
		self.logger    = logger.getChild ( 'metadata' )
		self._metadata = nodes.MetadataRoot()
		# reserved for future usage ("dominant ebuilds": when ebuildjobs
		# share one metadata instance etc.)
		self.package_info = None
		self.filename     = 'metadata.xml'
	# --- end of __init__ (...) ---

	def update ( self, package_info ):
		"""Updates the metadata using the given description data.

		It's expected that this method is called when Ebuild creation is done.

		arguments:
		* desc_data -- description data read from R package
		* package_info -- reserved for future usage

		returns: None (implicit)
		"""
		data = package_info ['desc_data']

		mref = self._metadata

		max_textline_width = roverlay.config.get ( 'METADATA.linewidth', 65 )


		description = None

		if USE_FULL_DESCRIPTION and 'Title' in data and 'Description' in data:
			description = data ['Title'] + ' // ' + data ['Description']

		elif 'Description' in data:
			description = ddata ['Description']

		elif 'Title' in data:
			description = data ['Title']

		#if description:
		if description is not None:
			mref.add (
				nodes.DescriptionNode ( description, linewidth=max_textline_width )
			)

		# these USE flags are described in profiles/use.desc,
		#  no need to include them here
		#mref.add_useflag ( 'byte-compile', 'enable byte-compiling' )
		#
		#if package_info ['has_suggests']:
		#	mref.add_useflag ( 'R_suggests', 'install optional dependencies' )

	# --- end of update (...) ---

	def write ( self, _file ):
		"""Writes the metadata into a file.

		arguments:
		* _file -- file to write, either a file handle or string in which case
		           a file object will be created

	  returns: True if writing succeeds, else False

	  raises: Exception if no metadata to write
	  """
		if self._metadata.empty():
			raise Exception ( "not enough metadata to write!" )
			#return False
		else:
			return self._metadata.write_file ( _file )
	# --- end of write (...) ---
