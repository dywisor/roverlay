# R Overlay -- ebuild creation, "master" module
# Copyright 2006-2012 Gentoo Foundation
# Distributed under the terms of the GNU General Public License v2

import threading
import logging

try:
	import queue
except ImportError:
	# python2
	import Queue as queue

from roverlay                 import config
from roverlay.ebuildjob       import EbuildJob
from roverlay.depres          import depresolver
from roverlay.depres.channels import EbuildJobChannel

class EbuildCreator ( object ):

	NUMTHREADS = config.get ( 'EBUILD.jobcount', 0 )

	def __init__ ( self ):
		"""Initializes an EbuildCreator. This is an Object that controls the
		R package -> ebuild creation. It continuously creates EbuildJobs for
		every R package added.
		"""
		self.ebuild_headers   = dict ()
		self.depresolve_main  = depresolver.DependencyResolver ()

		self.ebuild_jobs      = queue.Queue()
		self.ebuild_jobs_done = list()

		self.runlock  = threading.Lock()
		self._threads = None

		self.logger   = logging.getLogger ( 'EbuildCreator' )

	# --- end of init (...) ---

	def add_package ( self, package_file ):
		"""Adds an R package to the EbuildCreator, which means that an EbuildJob
		will be created for it. Returns the EbuildJob, which is also stored
		in the job queue.

		arguments:
		* package_file -- path R package file
		"""

		new_job = EbuildJob ( package_file, self.get_resolver_channel )

		self.ebuild_jobs.put ( new_job )

		return new_job

	# --- end of add_package (...) ---

	def get_resolver_channel ( self, name=None ):
		"""Returns a communication channel to the dependency resolver.

		arguments:
		readonly -- whether the channel is listen-only (no write methods) or not
		            defaults to True
		"""
		return self.depresolve_main.register_channel ( EbuildJobChannel ( name=name ) )

	# --- end of get_resolver_channel (...) ---

	def close ( self ):
		self.depresolve_main.close()
	# --- end of close (...) ---

	def _thread_run ( self ):

		while not self.ebuild_jobs.empty():
			try:
				job = self.ebuild_jobs.get_nowait()
			except queue.Empty:
				# queue is empty, done
				return

			job.run()
			self.ebuild_jobs_done.append ( job )

	# --- end of _thread_run (...) ---

	def run ( self ):
		"""Tells all EbuildJobs to run."""

		if not self.runlock.acquire ( False ):
			# already running
			return True


		jobcount = EbuildCreator.NUMTHREADS

		if jobcount < 1:
			if jobcount < 0:
				self.logger.warning ( "Running in sequential mode." )
			else:
				self.logger.debug ( "Running in sequential mode." )
			self._thread_run()
		else:
			self.logger.warning (
				"Running in concurrent mode with %i jobs." % jobcount
			)
			self._threads = [
				threading.Thread ( target = self._thread_run )
				for n in range ( jobcount )
			]

			for t in self._threads: t.start()
			for t in self._threads: t.join()

			del self._threads
			self._threads = None


		self.runlock.release()

	# --- end of run (...) ---

	def collect_ebuilds ( self ):
		"""Returns all ebuilds. (They may not be ready / TODO)"""
		ebuilds = [ job.get_ebuild() for job in self.ebuild_jobs_done ]
		return filter ( None, ebuilds )

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
