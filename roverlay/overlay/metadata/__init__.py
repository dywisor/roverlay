# R Overlay -- ebuild creation, metadata creation
# Copyright 2006-2012 Gentoo Foundation
# Distributed under the terms of the GNU General Public License v2

import roverlay.config

from roverlay.overlay.metadata import nodes

USE_FULL_DESCRIPTION = True

class MetadataJob ( object ):
	"""R package description data -> metadata.xml interface."""

	def __init__ ( self, filepath, logger ):
		"""Initializes a MetadataJob.

		arguments:
		* filepath -- path where the metadata file will be written to
		* logger   -- parent logger to use
		"""
		self.logger        = logger.getChild ( 'metadata' )
		self._package_info = None
		self.filepath      = filepath
		# no longer storing self._metadata, which will only be created twice
		# when running show() (expected 1x write per PackageInfo instance)
	# --- end of __init__ (...) ---

	def empty ( self ):
		return self._package_info is None
	# --- end of empty (...) ---

	def update ( self, package_info ):
		"""Updates the metadata.
		Actually, this won't create any metadata, it will only set the
		PackageInfo object to be used for metadata creation.

		arguments:
		* package_info --
		"""
		if package_info.has ( 'desc_data' ) and \
			package_info.compare_version ( self._package_info ) > 0:
				self._package_info = package_info
	# --- end of update (...) ---

	def update_using_iterable ( self, package_info_iter ):
		for package_info in package_info_iter:
			self.update ( package_info )
	# --- end of update_using_iterable (...) ---

	def _create ( self ):
		"""Creates metadata (MetadataRoot) using the stored PackageInfo.

		It's expected that this method is called when Ebuild creation is done.

		returns: created metadata
		"""
		mref = nodes.MetadataRoot()
		data = self._package_info ['desc_data']

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

		return mref
	# --- end of update (...) ---

	def _write ( self, fh ):
		"""Writes the metadata into a file.

		arguments:
		* _file -- file to write, either a file handle or string in which case
		           a file object will be created

		returns: True if writing succeeds, else False

		raises: Exception if no metadata to write
		"""
		if self._create().write_file ( fh ):
			return True
		else:
			raise Exception ( "not enough metadata to write!" )
	# --- end of _write (...) ---

	show = _write

	def write ( self ):
		_success = False
		try:
			fh = open ( self.filepath, 'w' )
			self._write ( fh )
			_success = True
		except any as e:
			self.logger.exception ( e )
		finally:
			if 'fh' in locals() and fh: fh.close()

		return _success
	# --- end of write (...) ---
