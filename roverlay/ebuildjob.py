# R Overlay -- ebuild creation, "job" module
# Copyright 2006-2012 Gentoo Foundation
# Distributed under the terms of the GNU General Public License v2

from roverlay.fileio import DescriptionReader
from roverlay.ebuild import Ebuild

class EbuildJob:
	STATUS_LIST = [ 'INIT', 'BUSY', 'WAIT', 'SUCCESS', 'FAIL' ]
	STATUS_MAP  = dict ( ( name, code ) for code, name in enumerate ( STATUS_LIST ) )

	@classmethod
	def __init__ ( self, package_file, dep_resolver=None ):
		self.package_file = package_file
		self.dep_resolver = dep_resolver
		# get description reader from args?
		self.description_reader = DescriptionReader()

		self.ebuild = None

		self._status = 0 # todo

	# --- end of __init__ (...) ---

	@staticmethod
	def get_statuscode ( status_id ):
		if status_id == 'ALL':
			return EbuildJob.STATUS_LIST
		elif isinstance ( status_id, int ):
			if status_id > 0 and status_id < len ( STATUS_LIST ):
				return EbuildJob.STATUS_LIST [status_id]
		elif status_id in EbuildJob.STATUS_MAP:
			return EbuildJob.STATUS_MAP [status_id]

		return None

	# --- end of get_statuscode (...) ---

	@classmethod
	def status ( self, expected_status=None ):
		"""Returns the current status of this job or a bool that indicates
		whether to current status matches the expected one.

		arguments:
		* expected_status -- if not None: check if this job's state is expected_status
		"""
		if expected_status:
			if isinstance ( expected_status, int ):
				return bool ( self._status == expected_status )
			elif expected_status in EbuildJob.STATUS_MAP:
				return bool ( self._status == EbuildJob.STATUS_MAP [expected_status] )
			else:
				return False

		return self._status

		# --- end of status (...) ---

	@classmethod
	def get_ebuild ( self ):
		"""Returns the Ebuild that is created by this object. Note that you should
		check the status with status ( $TODO::EBUILD_READY ) before trying to use
		the Ebuild.
		##fixme: it is guaranteed that self.ebuild is None unless the Ebuild is successfully created##
		"""
		return self.ebuild

	# --- end of get_ebuild (...) ---

	@classmethod
	def _set_status ( self, new_status ):
		self._status = EbuildJob.get_statuscode ( new_status )
		return True

	# --- end of _set_status (...) ---


	@classmethod
	def run ( self ):
		"""Tells this EbuildJob to run. This means that it reads the package file,
		resolves dependencies (TODO) and creates an Ebuild object that is ready
		to be written into a file.
		"""

		# check status
		if not self.status ( 'INIT' ):
			return

		if not self._set_status ( 'BUSY' ):
			return False

		read_data = self.description_reader.readfile ( self.package_file )

		if read_data is None:
			# set status accordingly
			self._set_status ( 'FAIL' )
			return False

		fileinfo  = read_data ['fileinfo']
		desc      = read_data ['description_data']

		ebuild = Ebuild()

		have_description = False

		print ( str ( desc ) )

		if 'Title' in desc:
			have_description = True
			ebuild.add ( 'DESCRIPTION', desc ['Title'] )

		if 'Description' in desc:
			have_description = True
			ebuild.add ( 'DESCRIPTION', ( '// ' if have_description else '' ) + desc ['Description'] )

		if not have_description:
			ebuild.add ( 'DESCRIPTION', '<none>' )
		del have_description

		# origin is todo (sync module knows the package origin)
		ebuild.add ( 'PKG_ORIGIN', 'CRAN' )

		ebuild.add ( 'PKG_FILE', fileinfo ['package_file'] )

		ebuild.add ( 'ebuild_header', [ '# test header' ], False )

		##  have to resolve deps here

		# enter status that allows transferring ebuild -> self.ebuild
		if self._set_status ( 'WAIT' ):
			# finalize self.ebuild: forced text creation + make it readonly
			if ebuild.prepare ( True, True ):
				self.ebuild = ebuild
				return self._set_status ( 'SUCCESS' )

		self._set_status ( 'FAIL' )
		return False


	# --- end of run (...) ---
