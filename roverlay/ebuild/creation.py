# R Overlay -- ebuild creation, "job" module
# Copyright 2006-2012 Gentoo Foundation
# Distributed under the terms of the GNU General Public License v2

import logging

import roverlay.static.depres

from roverlay.ebuild.construction        import EbuildConstruction
from roverlay.rpackage.descriptionreader import DescriptionReader

# move this to const / config
DEPENDENCY_FIELDS = {
	'R_SUGGESTS' : [ 'Suggests' ],
	'DEPENDS'    : [ 'Depends', 'Imports' ],
	'RDEPENDS'   : [ 'LinkingTo', 'SystemRequirements' ]
}

LOGGER = logging.getLogger ( 'EbuildCreation' )

class EbuildCreation ( object ):

	def __init__ ( self, package_info, depres_channel_spawner=None ):

		self.logger = LOGGER.getChild ( package_info ['name'] )
		self.package_info = package_info

		if depres_channel_spawner is None:
			self.request_resolver = roverlay.static.depres.get_ebuild_channel
		else:
			self.request_resolver = depres_channel_spawner

		# > 0 busy/working; 0 == done,success; < 0 done,fail
		self.status = 1

		self.package_info.set_readonly()
	# --- end of __init__ (...) ---

	def done()    : return self.status  < 1
	def busy()    : return self.status  > 0
	def success() : return self.status == 0
	def fail()    : return self.status  < 0


	def _resolve_dependencies ( self, ebuilder ):
		if self.request_resolver is None:
			self.logger.warning (
				"Cannot resolve dependencies, no resolver available!"
			)
			return True

		res = None
		# -- end pre func block --

		def init_channels():
			# collect dep strings and initialize resolver channels
			desc     = self.package_info ['desc_data']
			channels = dict()

			def get_resolver ( dependency_type ):
				if dependency_type not in channels:
					channels [dependency_type] = self.request_resolver (
						dependency_type,
						self.logger
					)
				return channels [dependency_type]
			# --- end of get_resolver (...) ---

			dep_type = desc_field = None

			for dep_type in DEPENDENCY_FIELDS:
				resolver = None

				for desc_field in DEPENDENCY_FIELDS [dep_type]:
					if desc_field in desc:
						if not resolver:
							resolver = get_resolver ( dep_type )

						if isinstance ( desc [desc_field], str ):
							resolver.add_dependency ( desc [desc_field] )
						elif hasattr ( desc [desc_field], '__iter__' ):
							resolver.add_dependencies ( desc [desc_field] )
						else:
							logger.warning (
								"Cannot add dependency '%s'." % desc [desc_field]
						)
					# -- if desc_field
				# -- for desc_field
			# -- for dep_type
			return channels
		# --- end of init_resolvers (...) ---

		def try_resolve():
			for r in res.values():
				if r.satisfy_request() is None:
					return False
			return True
		# --- end of try_resolve (...) ---

		# TODO
		# replace try_resolve with
		#  False in ( r.satisfy_request() for r in res.values() )
		# ?
		res     = init_channels()
		if not res: return True
		success = False


		if try_resolve():
			for dep_type, resolver in res.items():
				deplist = list ( filter ( None, resolver.collect_dependencies() ) )

				if deplist is None:
					## FIXME: false positive: "empty" channel
					raise Exception (
						'dep_resolver is broken: '
						'lookup() returns None but satisfy_request() says ok.'
					)
				elif hasattr ( deplist, '__iter__' ):
					# add dependencies in no_append/override mode
					self.logger.debug ( "adding %s to %s", deplist, dep_type )
					ebuilder.add ( dep_type, deplist, False )
				else:
					raise Exception ( "dep_resolver is broken: iterable expected!" )
			# -- for dep_type,..

			success = True

		# tell the dep resolver channels that we're done
		for r in res.values(): r.close()
		return success
	# --- end of resolve_dependencies (...) ---

	def _make_ebuild ( self ):
		desc = self.package_info ['desc_data']
		if desc is None:
			self.logger (
				'desc empty- cannot create an ebuild for this package.'
			)
			return None

		ebuilder = EbuildConstruction ( self.logger )

		have_desc = False

		if 'Title' in desc:
			ebuilder.add ( 'DESCRIPTION', desc ['Title'] )
			have_desc = True

		if 'Description' in desc:
			ebuilder.add (
				'DESCRIPTION',
				( '// ' if have_description else '' ) + desc ['Description']
			)


		ebuilder.add ( 'SRC_URI', self.package_info ['package_url'] )

		if self._resolve_dependencies():
			return ( ebuilder.get_ebuild(), ebuilder.has_rsuggests )

		return None
	# --- end of _make_ebuild (...) ---

	def run ( self ):
		if self.status < 1:
			raise Exception ( "Cannot run again." )

		try:
			if self.package_info.get ( 'desc_data',
				fallback_value=None, do_fallback=True ) is None:

				logging.warning ( 'Reading description data now.' )
				reader = DescriptionReader (
					self.package_info,
					logger=self.logger,
					read_now=True
				)
				self.package_info.set_writeable()
				self.package_info.update (
					desc_data=reader.get_desc ( run_if_unset=False )
				)
				del reader
			# -- if

			self.package_info.set_readonly()

			ebuild_info = self._make_ebuild()
			if ebuild_info is None:
				self.status = -1
			else:
				self.package_info.set_writeable()
				self.package_info.update (
					ebuild=ebuild_info   [0],
					suggests=ebuild_info [1]
				)
				self.package_info.set_readonly()
				self.status = 0
		except Exception as e:
			# log this and set status to fail
			self.status = -10
			self.logger.exception ( e )
	# --- end of run (...) ---
