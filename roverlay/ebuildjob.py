# R Overlay -- ebuild creation, "job" module
# Copyright 2006-2012 Gentoo Foundation
# Distributed under the terms of the GNU General Public License v2

from roverlay.fileio import DescriptionReader
from roverlay.ebuild import Ebuild

class EbuildJob:
	# move this to const / config
	DEPENDENCY_FIELDS = {
		'R_SUGGESTS' : [ 'Suggests' ],
		'DEPENDS'    : ['Depends', 'Imports' ],
		'RDEPENDS'   : [ 'LinkingTo', 'SystemRequirements' ]
	}

	##


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

	def __init__ ( self, package_file, dep_resolver=None ):
		"""Initializes an EbuildJob, which creates an ebuild for an R package.

		arguments:
		* package_file -- path to the R package file
		* dep_resolver -- dependency resolver
		"""

		"""Note:
		it is intended to run this job as thread, that's why it has its own
		dep resolver 'communication channel', status codes etc.
		"""

		self.package_file = package_file
		self.dep_resolver = dep_resolver
		# get description reader from args?
		self.description_reader = DescriptionReader()

		self.ebuild = None

		self.status = 'INIT'

	# --- end of __init__ (...) ---

	def get_ebuild ( self ):
		"""Returns the Ebuild that is created by this object. Note that you should
		check the status with status ( $TODO::EBUILD_READY ) before trying to use
		the Ebuild.
		##fixme: it is guaranteed that self.ebuild is None unless the Ebuild is successfully created##
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
		return get_status ( 'SUCCESS' )

	# --- end of done_success (...) ---


	def run ( self ):
		"""Tells this EbuildJob to run. This means that it reads the package file,
		resolves dependencies using its resolver (TODO) and creates
		an Ebuild object that is ready to be written into a file.
		"""

		# TODO move hardcoded entries to config/const

		try:

			# set status or return
			if not self._set_status ( 'BUSY', True ): return

			read_data = self.description_reader.readfile ( self.package_file )

			if read_data is None:
				# set status accordingly
				self._set_status ( 'FAIL' )
				return

			fileinfo  = read_data ['fileinfo']
			desc      = read_data ['description_data']

			ebuild = Ebuild()

			have_description = False

			if 'Title' in desc:
				ebuild.add ( 'DESCRIPTION', desc ['Title'] )
				have_description = True

			if 'Description' in desc:
				ebuild.add ( 'DESCRIPTION', ( '// ' if have_description else '' ) + desc ['Description'] )
				#have_description=True


			# origin is todo (sync module knows the package origin)
			ebuild.add ( 'PKG_ORIGIN', 'CRAN/BIOC/... TODO!' )
			ebuild.add ( 'SRC_URI', 'where? TODO!' )

			ebuild.add ( 'PKG_FILE', fileinfo ['package_file'] )

			ebuild.add ( 'ebuild_header',
								[ '# test header, first line\n',
									'# test header, second line\n\n\n\n',
									'#third\n\n#fifth' ],
								False
							)

			if self.dep_resolver and self.dep_resolver.enabled():

				# collect depdencies from desc and add them to the resolver
				raw_depends = dict ()

				dep_type = field = None

				for dep_type in EbuildJob.DEPENDENCY_FIELDS.keys():

					raw_depends [dep_type] = []

					for field in EbuildJob.DEPENDENCY_FIELDS [dep_type]:

						if field in desc:
							if isinstance ( desc [field], list ):
								raw_depends.extend ( desc [field] )
								self.dep_resolver.add_dependencies ( desc [field] )

							else:
								raw_depends.append ( desc [field] )
								self.dep_resolver.add_depency ( desc [field] )

				del field, dep_type


				while not self.dep_resolver.done():

					if not self._set_status ( 'WAIT_RESOLVE' ): return

					# tell the resolver to run (again)
					self.dep_resolver.run()

					if not self._set_status ( 'BUSY' ): return

				if self.dep_resolver.satisfy_request():

					dep_type = dep_str = dep = None

					# dependencies resolved, add them to the ebuild
					for dep_type in raw_depends.keys():

						for dep_str in raw_depends [dep_type]:
							# lookup (str) should return a str here
							dep = self.dep_resolver.lookup ( dep_str )
							if dep is None:
								raise Exception (
									"dep_resolver is broken: lookup() returns None but satisfy_request() says ok."
								)
							else:
								# add depencies in append mode
								dep = self.dep_resolver.lookup ( dep_str )
								ebuild.add ( dep_type,
													self.dep_resolver.lookup ( dep_str ),
													True
												)

					del dep, dep_str, dep_type

					# tell the dep resolver that we're done here
					self.dep_resolver.close()

				else:
					# ebuild is not creatable, set status to FAIL and close dep resolver
					self._set_status ( 'FAIL' )
					self.dep_resolver.close()
					return

			## finalize self.ebuild: forced text creation + make it readonly
			if ebuild.prepare ( True, True ):
				self.ebuild = ebuild

			return None

		except Exception as any_exception:
			# any exception means failure
			self.status = 'FAIL'
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
			self.status = new_status

		if new_status and new_status in EbuildJob.STATUS_LIST:
			# check if jumping from self.status to new_status is allowed
			if new_status in EbuildJob.STATUS_BRANCHMAP [self.status]:
				self.status = new_status
				return True

		# default return
		return False

	# --- end of _set_status (...) ---
