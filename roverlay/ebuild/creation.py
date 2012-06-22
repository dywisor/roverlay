# R Overlay -- ebuild creation
# Copyright 2006-2012 Gentoo Foundation
# Distributed under the terms of the GNU General Public License v2

import logging

from roverlay.ebuild                     import depres, ebuilder, evars
from roverlay.rpackage.descriptionreader import DescriptionReader


LOGGER = logging.getLogger ( 'EbuildCreation' )

# USE_FULL_DESCRIPTION
#  * True: use Title and Description for ebuild's DESCRIPTION variable
#  * else: use Title _or_ Description
USE_FULL_DESCRIPTION = False

# FALLBACK_DESCRIPTION is used as DESCRIPTION= value if not empty and
#  the R package has no Title/Description
FALLBACK_DESCRIPTION = "<none>"

class EbuildCreation ( object ):
	"""Used to create an ebuild using DESCRIPTION data."""

	def __init__ ( self, package_info, depres_channel_spawner=None ):
		"""Initializes the creation of an ebuild.

		arguments:
		* package_info           --
		* depres_channel_spawner -- function that returns a communication
		                             channel to the resolver
		"""
		self.package_info = package_info

		self.logger = LOGGER.getChild ( package_info ['name'] )

		# > 0 busy/working; 0 == done,success; < 0 done,fail
		self.status = 1

		self.depres_channel_spawner = depres_channel_spawner

		self.package_info.set_readonly()
	# --- end of __init__ (...) ---

	def done    ( self ) : return self.status  < 1
	def busy    ( self ) : return self.status  > 0
	def success ( self ) : return self.status == 0
	def fail    ( self ) : return self.status  < 0

	def run ( self ):
		"""Creates an ebuild. Returns None (implicit)."""
		if self.status < 1:
			raise Exception ( "Cannot run again." )

		try:
			self._lazyimport_desc_data()

			self.package_info.set_readonly()

			if self._make_ebuild():
				self.logger.debug ( "Ebuild is ready." )
				self.status = 0
			else:
				self.logger.info ( "Cannot create an ebuild for this package." )
				self.status = -1

		except Exception as e:
			# log this and set status to fail
			self.status = -10
			self.logger.exception ( e )
	# --- end of run (...) ---

	def _lazyimport_desc_data ( self ):
		"""Reads R package description data."""
		# TODO/FIXME: read this somewhere else?
		if self.package_info.get ( 'desc_data',
			fallback_value=None, do_fallback=True ) is None:

			logging.warning ( 'Reading description data now.' )
			reader = DescriptionReader (
				self.package_info,
				logger=self.logger,
				read_now=True
			)
			self.package_info.set_writeable()
			self.package_info.update (
				desc_data=reader.get_desc ( run_if_unset=False )
			)
			del reader

	# --- end of _lazyimport_desc_data (...) ---

	def _get_ebuild_description ( self ):
		"""Creates a DESCRIPTION variable."""
		desc = self.package_info ['desc_data']

		description = None
		if USE_FULL_DESCRIPTION:
			# use Title and Description for DESCRIPTION=
			if 'Title' in desc:
				description = desc ['Title']

			if 'Description' in desc:
				if description is None:
					description = desc ['Description']
				else:
					description += '// ' + desc ['Description']
		else:
			# use either Title or Description for DESCRIPTION=
			# (Title preferred 'cause it should be shorter)
			if 'Title' in desc:
				description = desc ['Title']
			elif 'Description' in desc:
				description = desc ['Description']


		if description is not None:
			return evars.DESCRIPTION ( description )
		elif FALLBACK_DESCRIPTION:
			return evars.DESCRIPTION ( FALLBACK_DESCRIPTION )
		else:
			return None
	# --- end of _get_ebuild_description (...) ---

	def _make_ebuild ( self ):
		"""Tries to create ebuild data."""
		if self.package_info ['desc_data'] is None:
			self.logger (
				'desc empty - cannot create an ebuild for this package.'
			)
			return False

		_dep_resolution = depres.EbuildDepRes (
			self.package_info, self.logger,
			create_iuse=True, run_now=True,
			depres_channel_spawner=self.depres_channel_spawner
		)
		if not _dep_resolution.success():
			# log here? (FIXME)
			return False


		dep_result = _dep_resolution.get_result()

		ebuild = ebuilder.Ebuilder()

		# add *DEPEND, IUSE to the ebuild
		ebuild.use ( *dep_result [1] )

		# DESCRIPTION
		ebuild.use ( self._get_ebuild_description() )

		# SRC_URI
		ebuild.use ( evars.SRC_URI ( self.package_info ['SRC_URI'] ) )

		ebuild_text = ebuild.to_str()

		self.package_info.update_now (
			ebuild=ebuild_text,
			depres_result=dep_result
		)

		return True
	# --- end of _make_ebuild (...) ---
