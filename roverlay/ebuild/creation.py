# R overlay -- ebuild creation
# -*- coding: utf-8 -*-
# Copyright (C) 2012 André Erdmann <dywi@mailerd.de>
# Distributed under the terms of the GNU General Public License;
# either version 2 of the License, or (at your option) any later version.

"""ebuild creation

This module puts all parts of the ebuild package together and provides
easy-to-use ebuild creation access.
"""

__all__ = [ 'EbuildCreation', ]

import logging

from roverlay.ebuild import depres, ebuilder, evars

EMPTY_ITERABLE = tuple()

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

	def __init__ ( self, package_info, err_queue, depres_channel_spawner=None ):
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

		self.err_queue = err_queue

		self.package_info.set_readonly()
	# --- end of __init__ (...) ---

	#def done    ( self ) : return self.status  < 1
	#def busy    ( self ) : return self.status  > 0
	#def success ( self ) : return self.status == 0
	#def fail    ( self ) : return self.status  < 0

	def run ( self ):
		"""Creates an ebuild and stores it directly in the assigned PackageInfo
		instance. Returns None (implicit)."""
		if self.status < 1:
			raise Exception ( "Cannot run again." )

		try:
			self.package_info.update_now ( make_desc_data=True )

			if self._make_ebuild():
				self.logger.debug ( "Ebuild is ready." )
				self.status = 0
			else:
				self.logger.info ( "Cannot create an ebuild for this package." )
				self.status = -1

		except ( Exception, KeyboardInterrupt ):
			# set status to fail
			self.status = -10
			raise
	# --- end of run (...) ---

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
		# TODO rewrite this function
		#  if overriding (R)DEPEND,IUSE vars is required

		if self.package_info ['desc_data'] is None:
			self.logger.warning (
				'desc empty - cannot create an ebuild for this package.'
			)
			return False

		_dep_resolution = depres.EbuildDepRes (
			self.package_info, self.logger,
			create_iuse=True, run_now=True,
			depres_channel_spawner=self.depres_channel_spawner,
			err_queue=self.err_queue
		)

		if _dep_resolution.success():
			dep_result = _dep_resolution.get_result()

			ebuild = ebuilder.Ebuilder()

			ebuild.use ( *self.package_info.get ( 'EVAR', EMPTY_ITERABLE ) )
			#evars_overridden = tuple ( ebuild.get_names() )
			# if k.name not in evars_overridden: ebuild.use ( k )

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

		else:
			return False
	# --- end of _make_ebuild (...) ---
