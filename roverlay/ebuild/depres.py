# R Overlay -- ebuild creation, <?>
# Copyright 2006-2012 Gentoo Foundation
# Distributed under the terms of the GNU General Public License v2

import roverlay.static.depres

from roverlay.ebuild import evars

# move this to const / config
FIELDS = {
	'R_SUGGESTS' : [ 'Suggests' ],
	'DEPENDS'    : [ 'Depends', 'Imports' ],
	'RDEPENDS'   : [ 'LinkingTo', 'SystemRequirements' ]
}

EBUILDVARS = {
	'R_SUGGESTS' : evars.R_SUGGESTS,
	'DEPENDS'    : evars.DEPEND,
	'RDEPENDS'   : evars.RDEPEND,
}


class EbuildDepRes ( object ):

	def __init__ (
		self, package_info, logger,
		depres_channel_spawner=None, create_iuse=True, run_now=True
	):
		self.logger       = logger
		self.package_info = package_info

		if depres_channel_spawner is None:
			self.request_resolver = roverlay.static.depres.get_ebuild_channel
		else:
			self.request_resolver = depres_channel_spawner

		# > 0 busy/working; 0 == done,success; < 0 done,fail
		self.status       = 1
		self.result       = None
		self.has_suggests = None
		self.create_iuse  = create_iuse

		self._channels    = None

		if run_now:
			self.resolve()

	# --- end of __init__ (...) ---

	def done    ( self ) : return self.status  < 1
	def busy    ( self ) : return self.status  > 0
	def success ( self ) : return self.status == 0
	def fail    ( self ) : return self.status  < 0

	def get_result ( self ):
		return ( self.status, self.result, self.has_suggests )
	# --- end of get_result (...) ---

	def resolve ( self ):
		try:
			self.result = None
			self._init_channels()

			if self._wait_resolve():
				self._make_result()
				self.status = 0

			else:
				# unresolvable
				self.logger.info ( "Cannot satisfy dependencies!" )

				self.result = None
				self.status = -5

		finally:
			self._close_channels()
	# --- end of resolve (...) ---

	def _get_channel ( self, dependency_type ):
		if dependency_type not in self._channels:
			self._channels [dependency_type] = self.request_resolver (
				dependency_type,
				self.logger
			)
		return self._channels [dependency_type]
	# --- end of get_channel (...) ---

	def _init_channels ( self ):
		# collect dep strings and initialize resolver channels

		if self.request_resolver is None:
			self.logger.warning (
				"Cannot resolve dependencies, no resolver available!"
			)
			return True

		desc = self.package_info ['desc_data']
		self._channels = dict()

		dep_type = desc_field = None

		for dep_type in FIELDS:
			resolver = None

			for desc_field in FIELDS [dep_type]:
				if desc_field in desc:
					if not resolver:
						resolver = self._get_channel ( dep_type )

					if isinstance ( desc [desc_field], str ):
						resolver.add_dependency ( desc [desc_field] )
					elif hasattr ( desc [desc_field], '__iter__' ):
						resolver.add_dependencies ( desc [desc_field] )
					else:
						logger.warning (
							"Cannot add dependency '%s'." % desc [desc_field]
					)
		# -- for dep_type

		self.has_suggests = bool ( 'R_SUGGESTS' in self._channels )

	# --- end of _init_channels (...) ---

	def _close_channels ( self ):
		if self._channels is None: return

		for channel in self._channels.values(): channel.close()
		del self._channels
	# --- end of _close_channels (...) ---

	def _wait_resolve ( self ):
		# True if no channels
		for c in self._channels.values():
			if c.satisfy_request() is None:
				return False
		return True
	# --- end of _wait_resolve (...) ---

	def _make_result ( self ):
		_result = list()
		for dep_type, channel in self._channels.items():
			deplist = list ( filter ( None, channel.collect_dependencies() ) )

			if deplist is None:
				## FIXME: false positive: "empty" channel
				raise Exception (
					'dep_resolver is broken: '
					'lookup() returns None but satisfy_request() says ok.'
				)
			elif hasattr ( deplist, '__iter__' ):
				# add dependencies in no_append/override mode
				self.logger.debug ( "adding %s to %s", deplist, dep_type )
				_result.append (
					EBUILDVARS [dep_type] (
						deplist,
						using_suggests=self.has_suggests
					)
				)
			else:
				raise Exception ( "dep_resolver is broken: iterable expected!" )
		# -- for dep_type,..

		if self.create_iuse:
			_result.append ( evars.IUSE ( using_suggests=self.has_suggests ) )

		self.result = tuple ( _result )
	# --- end of _make_result (...) ---
