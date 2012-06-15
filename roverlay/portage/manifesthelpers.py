# R Overlay -- Manifest creation for ebuilds
# Copyright 2006-2012 Gentoo Foundation
# Distributed under the terms of the GNU General Public License v2


# TODO (in future): could use portage api directly, namely
#  '/usr/lib/portage/pym/portage/package/ebuild/doebuild.py'
# instead of using '/usr/bin/ebuild'

import os
import copy
import logging
import subprocess


from roverlay import config, util


class ManifestCreation ( object ):
	"""This is the base class for Manifest file creation."""

	static_instance = None

	def __init__ ( self ):
		self.logger = logging.getLogger ( 'ManifestCreation' )
	# --- end of __init__ (...) ---

	def create_for ( self, package_info ):
		"""Creates a Manifest file for the ebuild of the given package_info."""
		raise Exception ( "method stub" )
	# --- end of create_for (...) ---

	@classmethod
	def do ( cls, package_info ):
		"""Class/static access to Manifest creation."""
		if cls.static_instance is None:
			cls.static_instance = cls()

		return cls.static_instance.create_for ( package_info )
	# --- end of do (...) ---


class ExternalManifestCreation ( ManifestCreation ):
	"""This class implements Manifest creation using the low level ebuild
	interface, ebuild(1), which is called in a filtered environment.
	"""

	def __init__ ( self ):
		super ( ExternalManifestCreation, self ) . __init__ ()
		self.manifest_env = ManifestEnv ( filter_env=True )
		self.ebuild_prog  = config.get ( 'TOOLS.EBUILD.prog', '/usr/bin/ebuild' )
		# ebuild <ebuild_file> <target>, where target is:
		self.ebuild_tgt   = config.get ( 'TOOLS.EBUILD.target', 'manifest' )
	# --- end of __init__ (...) ---

	def create_for ( self, package_info ):
		"""See ManifestCreation.create_for.
		Calls ebuild, returns True on success else False.

		raises: *passes Exceptions from failed config lookups
		"""


		my_env = self.manifest_env [ package_info ['origin'] ]

		ebuild_file = util.get_extra_packageinfo ( package_info, 'EBUILD_FILE' )

		ebuild_call = subprocess.Popen (
			(
				self.ebuild_prog,
				ebuild_file,
				self.ebuild_tgt
			),
			stdin=None,
			stdout=subprocess.PIPE,
			stderr=subprocess.PIPE,
			env=my_env
		)


		output = ebuild_call.communicate()
		# necessary? (probably not, FIXME/TODO)
		ebuild_call.wait()

		# log stdout?
		#for line in util.pipe_lines ( output [0] ):
		#	LOGGER.debug ( line )

		# log stderr
		for line in util.pipe_lines ( output [1], use_filter=True ):
			self.logger.warning ( line )

		if ebuild_call.returncode == 0:
			return True
		else:
			self.logger.error ( "Couldn't create Manifest for %s!" % ebuild_file )
			return False
	# --- end of create_for (...) ---


class ManifestEnv ( object ):
	"""per-repo environment container for Manifest creation using ebuild."""

	def __init__ ( self, filter_env=True ):
		"""Initializes a ManifestEnv.

		arguments:
		* filter_env -- if True: start with an empty env and copy vars
										 from os.environ selectively
							 else   : start with os.environ as env
		"""
		self.filter_env  = filter_env
		self._manenv     = dict()
		self.logger      = logging.getLogger ( 'ManifestEnv' )
		self._common_env = None
	# --- end of __init__ (...) ---

	def get_env ( self, repo_name ):
		"""Returns an env dict for repo_name.

		arguments:
		* repo_name --
		"""
		if not repo_name in self._manenv:
			repo_env                 = self._get_common_manifest_env()
			repo_env ['DISTDIR']     = util.get_distdir ( repo_name )
			self._manenv [repo_name] = repo_env

		return self._manenv [repo_name]
	# --- end of get_env (...) ---

	# x = ManifestEnv(); env = x [repo] etc.
	__getitem__ = get_env

	def _get_common_manifest_env ( self, noret=False ):
		"""Creates an environment suitable for an
		"ebuild <ebuild> digest|manifest" call (or uses an already existing env).
		Returns a shallow copy of this env which can then be locally modified
		(setting DISTDIR).

		arguments:
		* noret -- do not return copied env if True
		"""

		if self._common_env is None:
			# ((lock this if required))

			if self.filter_env:

				# selectively import os.environ
				# FIXME: keep EBUILD_DEFAULT_OPTS?
				our_env = util.keepenv (
					( 'PATH', '' ),
					'LANG',
					'PWD',
					'EBUILD_DEFAULT_OPTS'
				)
			else:
				# copy os.environ
				our_env = dict ( os.environ )

			# -- common env part

			# set FEATURES
			# * digest -- needed? (works without it)
			# * assume-digests --
			# * unknown-features-warn -- should FEATURES ever change
			#
			# * noauto -- should prevent ebuild from adding additional actions,
			#   it still tries to download source packages, which is just wrong
			#    here 'cause it is expected that the R package file exists when
			#   calling this function, so FETCHCOMMAND/RESUMECOMMAND will be set
			#   to /bin/true if possible.
			#
			# * distlocks -- disabled if FETCHCOMMAND/RESUMECOMMAND set to no-op
			#
			our_env ['FEATURES'] = \
				"noauto digest assume-digests unknown-features-warn"

			# try to prevent src fetching
			for nop in ( '/bin/true', '/bin/echo' ):
				if os.path.isfile ( nop ):
					self.logger.debug (
						'%s disables/replaces FETCHCOMMAND/RESUMECOMMAND' % nop
					)
					fetch_nop = "%s \${DISTDIR} \${FILE} \${URI}" % nop
					our_env ['FETCHCOMMAND']  = fetch_nop
					our_env ['RESUMECOMMAND'] = fetch_nop
					our_env ['FEATURES']     += " -distlocks"
					break

			# set PORDIR_OVERLAY
			our_env ['PORTDIR_OVERLAY'] = config.get_or_fail (
				[ 'OVERLAY', 'dir' ]
			)

			self._common_env = our_env
		# -- end if
		if noret:
			return None
		else:
			return copy.copy ( self._common_env )
	# --- end of _get_common_manifest_env (...) ---




