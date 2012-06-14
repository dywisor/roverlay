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

EBUILD_PROG   = config.get ( 'TOOLS.EBUILD.prog', '/usr/bin/ebuild' )
EBUILD_TARGET = config.get ( 'TOOLS.EBUILD.target', 'manifest' )

LOGGER = logging.getLogger ( 'ManifestCreation' )

_MANIFEST_ENV = [ None, None ]

def _get_manifest_env ( filter_env=True ):
	"""Creates an environment suitable for an "ebuild <ebuild> digest|manifest"
	call (or uses an already existing env).
	Returns a shallow copy of this env which can then be locally modified
	(setting DISTDIR).
	TODO/FIXME: DISTDIR is per repo, so use one env per repo!

	arguments:
	* filter_env -- if True: start with an empty env and copy vars
	                         from os.environ selectively
	                else   : start with os.environ as env
	"""

	mindex = 0 if filter_env else 1

	if _MANIFEST_ENV [mindex] is None:
		# ((lock this if required))

		if filter_env:

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
		# * noauto -- should prevent ebuild from adding additional actions,
		#   it still tries to download source packages, which is just wrong here
		#   'cause it is expected that the R package file exists when calling
		#   this function, so FETCHCOMMAND/RESUMECOMMAND will be set
		#   to /bin/true if possible.
		# * distlocks -- disabled if FETCHCOMMAND/RESUMECOMMAND set to no-op
		#
		our_env ['FEATURES'] = \
			"noauto digest assume-digests unknown-features-warn"

		# try to prevent src fetching
		for nop in ( '/bin/true', '/bin/echo' ):
			if os.path.isfile ( nop ):
				fetch_nop = "%s \${DISTDIR} \${FILE} \${URI}" % nop
				our_env ['FETCHCOMMAND']  = fetch_nop
				our_env ['RESUMECOMMAND'] = fetch_nop
				our_env ['FEATURES']     += " -distlocks"
				break

		# set PORDIR_OVERLAY
		our_env ['PORTDIR_OVERLAY'] = config.get_or_fail ( [ 'OVERLAY', 'dir' ] )

		_MANIFEST_ENV [mindex] = our_env
	# -- end if
	return copy.copy ( _MANIFEST_ENV [mindex] )
# --- end of _get_manifest_env (...) ---

def create_manifest ( package_info ):

	my_env = _get_manifest_env ( filter_env=True )

	# using util for reading package info
	my_env ['DISTDIR']  = util.get_extra_packageinfo (
		package_info, 'PKG_DISTDIR'
	)

	ebuild_file = util.get_extra_packageinfo ( package_info, 'EBUILD_FILE' )

	ebuild_call = subprocess.Popen (
		(
			EBUILD_PROG,
			'--debug',
			ebuild_file,
			EBUILD_TARGET
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
		LOGGER.warning ( line )

	if ebuild_call.returncode == 0:
		return True
	else:
		LOGGER.error ( "Cannot create Manifest for %s!" % ebuild_file )
		return False
# --- end of create_manifest (...) ---

def try_manifest ( package_info ):
	try:
		return create_manifest ( package_info )
	except Exception as any_exception:
		LOGGER.exception ( any_exception )
		return False
# --- end of try_manifest (...) ---

t = try_manifest


