# R Overlay -- Manifest creation for ebuilds
# Copyright 2006-2012 Gentoo Foundation
# Distributed under the terms of the GNU General Public License v2

# TODO (in future): could use portage api directly, namely
#  '/usr/lib/portage/pym/portage/package/ebuild/doebuild.py'
# instead of using '/usr/bin/ebuild'

import os.path
import copy
import logging
import subprocess


from roverlay import config, util

from roverlay.overlay.manifest.env import ManifestEnv

class ExternalManifestCreation ( object ):
	"""This class implements Manifest creation using the low level ebuild
	interface, ebuild(1), which is called in a filtered environment.
	"""
	# NOTE:
	# ebuild <ebuild> digest does not support multiprocesses for one overlay,

	def __init__ ( self ):
		self.logger       = logging.getLogger ( 'ManifestCreation' )
		self.manifest_env = ManifestEnv.get_new()
		self.ebuild_tgt   = config.get ( 'TOOLS.EBUILD.target', 'manifest' )
		self.ebuild_prog  = config.get ( 'TOOLS.EBUILD.prog', '/usr/bin/ebuild' )

		# set PORDIR_OVERLAY and DISTDIR
		self.manifest_env ['PORTDIR_OVERLAY'] = config.get_or_fail (
			'OVERLAY.dir'
		)
		# !! FIXME: tell the <others> that __tmp__ is a reserved directory
		self.manifest_env ['DISTDIR'] = \
		config.get_or_fail ( 'DISTFILES.ROOT' ) + os.path.sep + '__tmp__'


	# --- end of __init__ (...) ---

	def create_for ( self, package_info_list ):
		"""See ManifestCreation.create_for.
		Calls ebuild, returns True on success else False.

		raises: *passes Exceptions from failed config lookups
		"""
		self.logger.critical (
			"Manifest creation is broken! PORTAGE_RO_DISTDIRS does not work."
		)
		return False

		distdirs    = ' '.join ( set (
			p ['distdir'] for p in package_info_list
		) )
		ebuild_file = package_info_list [0] ['ebuild_file']


		self.manifest_env ['PORTAGE_RO_DISTDIRS'] = distdirs

		#util.dodir ( self.manifest_env ['DISTDIR'] )

		ebuild_call = subprocess.Popen (
			(
				self.ebuild_prog,
				ebuild_file,
				self.ebuild_tgt
			),
			stdin=None,
			stdout=subprocess.PIPE,
			stderr=subprocess.PIPE,
			env=self.manifest_env
		)

		output = ebuild_call.communicate()

		# log stdout?
		#for line in util.pipe_lines ( output [0] ):
		#	LOGGER.debug ( line )
		#for line in util.pipe_lines ( output [0] ): print ( line )

		# log stderr
		for line in util.pipe_lines ( output [1], use_filter=True ):
			self.logger.warning ( line )

		if ebuild_call.returncode == 0:
			self.logger.debug ( "Manifest written." )
			return True
		else:
			self.logger.error (
				'Couldn\'t create Manifest for {ebuild}! '
				'Return code was {ret}.'.format (
					ebuild=ebuild_file, ret=ebuild_call.returncode
				)
			)
			return False
	# --- end of create_for (...) ---
