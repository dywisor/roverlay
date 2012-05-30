# R Overlay -- ebuild creation, "master" module
# Copyright 2006-2012 Gentoo Foundation
# Distributed under the terms of the GNU General Public License v2

from roverlay.ebuildjob import EbuildJob

class EbuildCreator:

	def __init__ ( self ):
		"""Initializes an EbuildCreator. This is an Object that controls the
		R package -> ebuild creation. It continuously creates EbuildJobs for
		every R package added.
		"""
		self.ebuild_headers = dict ()
		self.depresolve_main = None # TODO
		self.ebuild_jobs = []

	# --- end of init (...) ---

	def add_package ( self, package_file ):
		"""Adds an R package to the EbuildCreator, which means that an EbuildJob
		will be created for it. Returns the EbuildJob, which is also stored
		in the job queue.

		arguments:
		* package_file -- path R package file
		"""

		new_job = EbuildJob ( package_file, self.get_resolver ( False ) )

		self.ebuild_jobs.append ( new_job )

		return new_job

	# --- end of add_package (...) ---

	def get_resolver ( self, readonly=True ):
		"""Returns a communication channel to the dependency resolver.

		arguments:
		readonly -- whether the channel is listen-only (no write methods) or not
		            defaults to True
		"""
		# <TODO>
		return None
		#return self.depresolve_main.get_channel()

	# --- end of get_resolver (...) ---

	def run ( self ):
		"""Tells all EbuildJobs to run."""
		for job in self.ebuild_jobs:
			job.run()

	# --- end of run (...) ---

	def collect_ebuilds ( self ):
		"""Returns all ebuilds. (They may not be ready / TODO)"""
		ebuilds = [ job.get_ebuild() for job in self.ebuild_jobs ]
		return [ ebuild for ebuild in ebuilds if (not ebuild is None) ]

	# --- end of collect_ebuilds (...) ---


	def get_ebuild_header ( self, ebuild_header_file=None ):
		"""Reads and returns the content of an ebuild header file.
		This is a normal file that can be included in ebuilds.
		Every header file will only be read on first access, its content will
		be stored in a dict that is shared among all EbuildCreator instances.

		arguments:
		* ebuild_header_file -- path to the header file; defaults to none which
		                        means that nothing will be read and an empty list
		                        is returned.
		"""

		if ebuild_header_file is None:
			# nothing to read
			return []

		elif ebuild_header_file in self.ebuild_headers:
			# previously read
			return self.ebuild_headers [ebuild_header_file]

		else:
			# read file
			try:
				fh = open ( ebuild_header_file, 'r' )
				lines = fh.readlines()
				fh.close()
				self.ebuild_headers [ebuild_header_file] = lines
				del fh
				return lines

			except IOError as err:
				# todo
				raise

	# --- end of get_ebuild_header (...) ---
