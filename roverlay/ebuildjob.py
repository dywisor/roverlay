# R Overlay -- ebuild creation, "job" module
# Copyright 2006-2012 Gentoo Foundation
# Distributed under the terms of the GNU General Public License v2

import logging
import re

from roverlay                   import config, util
from roverlay.ebuild            import Ebuild
from roverlay.descriptionreader import DescriptionReader



class EbuildJob ( object ):
	LOGGER = logging.getLogger ( 'EbuildJob' )

	DEFAULT_EBUILD_HEADER = config.get ( 'EBUILD.default_header' )

	# move this to const / config
	DEPENDENCY_FIELDS = {
		'R_SUGGESTS' : [ 'Suggests' ],
		'DEPENDS'    : [ 'Depends', 'Imports' ],
		'RDEPENDS'   : [ 'LinkingTo', 'SystemRequirements' ]
	}

	STATUS_LIST = [ 'INIT', 'BUSY', 'WAIT_RESOLVE', 'SUCCESS', 'FAIL' ]

	# status 'jump' control
	# FAIL is always allowed, S -> S has to be explicitly allowed
	STATUS_BRANCHMAP = dict (
		INIT         = [ 'BUSY' ],
		BUSY         = [ 'BUSY', 'WAIT_RESOLVE', 'SUCCESS' ],
		WAIT_RESOLVE = [ 'BUSY' ],
		SUCCESS      = [],
		FAIL         = [],
	)

	def __init__ ( self, package_file, depres_channel_spawner=None ):
		"""Initializes an EbuildJob, which creates an ebuild for an R package.

		arguments:
		* package_info -- R package file info
		* dep_resolver -- dependency resolver
		"""

		"""Note:
		it is intended to run this job as thread, that's why it has its own
		dep resolver 'communication channel', status codes etc.
		"""

		self.package_info = util.get_packageinfo ( package_file )

		try:
			self.logger = EbuildJob.LOGGER.getChild (
				self.package_info ['filename']
			)
		except KeyError:
			self.logger = EbuildJob.LOGGER.getChild ( '__undef__' )

		self.description_reader = DescriptionReader (
			self.package_info, logger=self.logger
		)

		self.ebuild = None

		# only allow a function (at least callable) for self.get_resolver
		if hasattr ( depres_channel_spawner, '__call__' ):
			self.request_resolver = depres_channel_spawner
			# _depres contains (almost) dependency resolution data/.., including
			# communication channels and should only be modified in run()
			self._depres = dict ()
		else:
			self.request_resolver = None

		self.status = 'INIT'

	# --- end of __init__ (...) ---

	def get_resolver ( self, dependency_type ):
		# comment TODO
		if not dependency_type in self._depres:
			self._depres [dependency_type] = \
				self.request_resolver ( dependency_type, self.logger )

		return self._depres [dependency_type]
	# --- end of get_resolver (...) ---

	def get_ebuild ( self ):
		"""Returns the Ebuild that is created by this object. Note that you should
		check the status with status ( $TODO::EBUILD_READY ) before trying to use
		the Ebuild.
		##fixme: it is (should be?) guaranteed that self.ebuild is None unless the Ebuild is successfully created##
		"""
		return self.ebuild

	# --- end of get_ebuild (...) ---

	def get_status ( self, expected_status=None ):
		"""Returns the current status of this job or a bool that indicates
		whether to current status matches the expected one.

		arguments:
		* expected_status -- if not None: check if this job's state is expected_status
		"""
		if not expected_status is None:
			return bool ( self.status == expected_status )
		else:
			return self.status

	# --- end of get_status (...) ---

	def done_success ( self ):
		"""Returns True if this has been successfully finished."""
		return self.get_status ( 'SUCCESS' )

	# --- end of done_success (...) ---

	def run ( self ):
		"""Tells this EbuildJob to run. This means that it reads the package file,
		resolves dependencies using its resolver (TODO) and creates
		an Ebuild object that is ready to be written into a file.
		"""

		# TODO move hardcoded entries to config/const
		# TODO metadata.xml creation (long DESCRIPTION should go into metadata, not the ebuild)

		try:

			# set status or return
			if not self._set_status ( 'BUSY', True ): return

			desc = self.description_reader.get_desc ( True )
			if desc is None:
				self._set_status ( 'FAIL' )
				self.logger.info ( 'Cannot create an ebuild for this package.' )


			fileinfo  = self.package_info

			ebuild = Ebuild ( self.logger.getChild ( "Ebuild" ) )

			ebuild.add ( 'pkg_name', fileinfo ['package_name'] )
			# TODO move regex to config/const
			ebuild.add ( 'pkg_version',
							re.sub ( '[-]{1,}', '.', fileinfo ['package_version'] )
							)


			have_description = False

			if 'Title' in desc:
				ebuild.add ( 'DESCRIPTION', desc ['Title'] )
				have_description = True

			if 'Description' in desc:
				ebuild.add ( 'DESCRIPTION', ( '// ' if have_description else '' ) + desc ['Description'] )
				#have_description=True


			# origin is todo (sync module knows the package origin)
			# could calculate SRC_URI in the eclass depending on origin
			##ebuild.add ( 'PKG_ORIGIN', 'CRAN/BIOC/... TODO!' )
			ebuild.add ( 'SRC_URI', 'where? TODO!' )

			ebuild.add ( 'PKG_FILE', fileinfo ['package_file'] )

			## default ebuild header, could use some const here (eclass name,..)
			ebuild.add ( 'ebuild_header',
								EbuildJob.DEFAULT_EBUILD_HEADER,
								False
							)

			if not self.request_resolver is None:

				dep_type = desc_field = None


				for dep_type in EbuildJob.DEPENDENCY_FIELDS:

					resolver = None

					for desc_field in EbuildJob.DEPENDENCY_FIELDS [dep_type]:

						if desc_field in desc:
							if not resolver:
								resolver = self.get_resolver ( dep_type )

							if isinstance ( desc [desc_field], list ):
								resolver.add_dependencies ( desc [desc_field] )

							else:
								resolver.add_depency ( desc [desc_field] )


				# lazy depres: wait until done and stop if any resolver channel
				# returns None (which implies failure)
				# wait for depres and store results
				resolved = True

				if not self._set_status ( 'WAIT_RESOLVE' ): return

				for resolver in self._depres.values():
					if resolver.satisfy_request() is None:
						resolved = False
						break

				if not self._set_status ( 'BUSY' ): return

				if not resolved:
					# ebuild is not creatable, set status to FAIL and close dep resolvers
					self.logger.info (
						"Failed to resolve dependencies for this package."
					)
					for r in self._depres.values(): r.close ()
					self._set_status ( 'FAIL' )
					return
				else:
					# add deps to the ebuild
					for dep_type, resolver in self._depres.items():
						# python3 requires list ( filter ( ... ) )
						deplist = list (
							filter ( None, resolver.collect_dependencies () )
						)

						if deplist is None:
							## FIXME: false positive: "empty" channel
								raise Exception (
									'dep_resolver is broken: '
									'lookup() returns None but satisfy_request() says ok.'
								)
						elif isinstance ( deplist, ( list, set ) ):
							# add dependencies in no_append/override mode
							self.logger.debug ( "adding %s to %s", str (deplist), dep_type )
							ebuild.add ( dep_type, deplist, False )

						else:
							raise Exception (
								"dep_resolver is broken: list or set expected!"
							)
					# --- end for


					# tell the dep resolver channels that we're done
					for r in self._depres.values(): r.close ()

			# --- end dep resolution


			## finalize self.ebuild: forced text creation + make it readonly
			if ebuild.prepare ( True, True ):
				self.ebuild = ebuild


		except Exception as any_exception:
			# any exception means failure
			self._set_status ( 'FAIL' )
			raise

	# --- end of run (...) ---

	def _set_status ( self, new_status, ignore_invalid=False ):
		"""Changes the status of this job. May refuse to do that if invalid change
		requested (e.g. 'FAIL' -> 'SUCCESS').

		arguments:
		new_status --
		"""

		if new_status == 'FAIL':
			# always allowed
			self.logger.info ( "Entering status '%s'.", new_status )
			self.status = new_status
			return True

		if new_status and new_status in EbuildJob.STATUS_LIST:
			# check if jumping from self.status to new_status is allowed
			if new_status in EbuildJob.STATUS_BRANCHMAP [self.status]:
				self.logger.debug ( "Entering status '%s'.", new_status )
				self.status = new_status
				return True

		# default return
		self.logger.error ( "Cannot enter status '%s'.", new_status )
		return False

	# --- end of _set_status (...) ---
