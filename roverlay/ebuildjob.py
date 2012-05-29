# R Overlay -- ebuild creation, "job" module
# Copyright 2006-2012 Gentoo Foundation
# Distributed under the terms of the GNU General Public License v2

from roverlay import ebuildcreator.EbuildCreator
from roverlay import fileio.DescriptionReader
from roverlay import ebuild.Ebuild

class EbuildJob:

	@classmethod
	def __init__ ( self, package_file, dep_resolver=None ):
		self.package_file = package_file
		self.dep_resolver = dep_resolver
		# get description reader from args?
		self.description_reader = DescriptionReader()
		self.ebuild = Ebuild()

		self.status = 0 # todo


	@classmethod
	def status ( self, expected_status=None ):
		"""Returns the current status of this job or a bool that indicates
		whether to current status matches the expected one.

		arguments:
		* expected_status -- if not None: check if this job's state is expected_status
		"""
		if expected_status:
			return self.status
		else:
			return bool ( self.status == expected_status )

	@classmethod
	def get_ebuild ( self ):
		"""Returns the Ebuild that is created by this object. Note that you should
		check the status with status ( $TODO::EBUILD_READY ) before trying to use
		the Ebuild.
		"""
		return self.ebuild


	@classmethod
	def run ( self ):
		"""Tells this EbuildJob to run. This means that it reads the package file,
		resolves dependencies (TODO) and creates an Ebuild object that is ready
		to be written into a file.
		"""

		# check status
		##

		read_data = self.description_reader.readfile ( self.package_file )

		if read_data is None
			# set status accordingly
			return None

		# transfer data from read_data to self.ebuild
		#  have to resolve deps here
		# <TODO>

		return None

