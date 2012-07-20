# R Overlay -- Manifest creation for ebuilds
# Copyright 2006-2012 Gentoo Foundation
# Distributed under the terms of the GNU General Public License v2

import os
import copy
import logging

from roverlay import util

class ManifestEnv ( object ):
	"""per-repo environment container for Manifest creation using ebuild."""

	@classmethod
	def get_new ( cls ):
		return cls ( filter_env=True ).get_env (
			distdir="", portage_ro_distdirs=""
		)
	# --- end of get_new (...) ---

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

	def get_env ( self, distdir, portage_ro_distdirs ):
		"""Returns an env dict for repo_dir.

		arguments:
		* repo_dir --
		"""
		env                         = self._get_common_manifest_env()
		env ['DISTDIR']             = distdir
		env ['PORTAGE_RO_DISTDIRS'] = portage_ro_distdirs
		return env
	# --- end of get_env (...) ---

	def _get_common_manifest_env ( self, noret=False ):
		"""Creates an environment suitable for an
		"ebuild <ebuild> digest|manifest" call (or uses an already existing env).
		Returns a shallow copy of this env which can then be locally modified
		(setting DISTDIR, PORTAGE_RO_DISTDIRS).

		arguments:
		* noret -- do not return copied env if True
		"""

		if self._common_env is None:

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
			#   here 'cause it is expected that the R package file exists when
			#   calling this function, so FETCHCOMMAND/RESUMECOMMAND will be set
			#   to /bin/true if possible.
			#
			# * distlocks -- disabled if FETCHCOMMAND/RESUMECOMMAND set to no-op
			#
			our_env ['FEATURES'] = \
				"noauto digest assume-digests unknown-features-warn"

			# try to prevent src fetching
			fetch_nop = util.sysnop (
				nop_returns_success=True,
				format_str="%s \${DISTDIR} \${FILE} \${URI}"
			)

			if not fetch_nop is None:
				self.logger.debug (
					fetch_nop [0] + " disables/replaces FETCHCOMMAND,RESUMECOMMAND."
				)
				our_env ['FETCHCOMMAND']  = fetch_nop [1]
				our_env ['RESUMECOMMAND'] = fetch_nop [1]
				our_env ['FEATURES']     += " -distlocks"


			self._common_env = our_env
		# -- end if
		if noret:
			return None
		else:
			return copy.copy ( self._common_env )
	# --- end of _get_common_manifest_env (...) ---
