# R Overlay -- ebuild creation, <?>
# Copyright 2006-2012 Gentoo Foundation
# Distributed under the terms of the GNU General Public License v2

from roverlay.depres import deptype
from roverlay.ebuild import evars

# TODO/FIXME/IGNORE move this to const / config
FIELDS_TO_EVAR = {
	'R_SUGGESTS' : ( 'Suggests', ),
	'DEPENDS'    : ( 'Depends', 'Imports' ),
	'RDEPENDS'   : ( 'LinkingTo', 'SystemRequirements' ),
	# ? : ( 'Enhances', )
}

# setting per-field dep types here, in accordance with
#  http://cran.r-project.org/doc/manuals/R-exts.html#The-DESCRIPTION-file
FIELDS = {
	# "The Depends field gives a comma-separated
	#  list of >>package names<< which this package depends on."
	'Depends'            : deptype.PKG,
	# "Other dependencies (>>external to the R system<<)
	#  should be listed in the SystemRequirements field"
	'SystemRequirements' : deptype.SYS,
	# "The Imports field lists >>packages<< whose namespaces
	#  are imported from (as specified in the NAMESPACE file)
	#  but which do not need to be attached."
	'Imports'            : deptype.PKG,
	# "The Suggests field uses the same syntax as Depends
	#  and lists >>packages<< that are >>not necessarily needed<<."
	'Suggests'           : deptype.internal,
	# "A package that wishes to make use of header files
	#  in other >>packages<< needs to declare them as
	#  a comma-separated list in the field LinkingTo in the DESCRIPTION file."
	'LinkingTo'          : deptype.PKG,
}
EBUILDVARS = {
	'R_SUGGESTS' : evars.R_SUGGESTS,
	'DEPENDS'    : evars.DEPEND,
	'RDEPENDS'   : evars.RDEPEND,
}


class EbuildDepRes ( object ):
	"""Handles dependency resolution for a single ebuild."""

	def __init__ (
		self, package_info, logger, depres_channel_spawner, err_queue,
		create_iuse=True, run_now=True,
	):
		"""Initializes an EbuildDepRes.

		arguments:
		* package_info           --
		* logger                 -- parent logger
		* depres_channel_spawner -- used to get channels to the dep resolver
		* create_iuse            -- create an IUSE evar (if True)
		* run_now                -- immediately start after initialization
		"""
		self.logger       = logger.getChild ( 'depres' )
		self.package_info = package_info

		self.request_resolver = depres_channel_spawner

		# > 0 busy/working; 0 == done,success; < 0 done,fail
		self.status       = 1
		self.result       = None
		self.has_suggests = None
		self.create_iuse  = create_iuse

		self.err_queue    = err_queue

		self._channels    = None

		if run_now:
			self.resolve()

	# --- end of __init__ (...) ---

	#def done    ( self ) : return self.status  < 1
	#def busy    ( self ) : return self.status  > 0
	def success ( self ) : return self.status == 0
	#def fail    ( self ) : return self.status  < 0

	def get_result ( self ):
		"""Returns the result of dependency resolution,
		as tuple ( <status>, <evars>, <has R suggests> )
		"""
		return ( self.status, self.result, self.has_suggests )
	# --- end of get_result (...) ---

	def resolve ( self ):
		"""Try to make/get dependency resolution results. Returns None."""
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
		"""Creates and returns a communication channel to the dep resolver."""
		if dependency_type not in self._channels:
			self._channels [dependency_type] = self.request_resolver (
				name=dependency_type,
				logger=self.logger,
				err_queue=self.err_queue,
			)
		return self._channels [dependency_type]
	# --- end of get_channel (...) ---

	def _init_channels ( self ):
		"""Initializes the resolver channels, one for each existing
		dependency type. Queues dependencies, too.
		"""
		# collect dep strings and initialize resolver channels

		if self.request_resolver is None:
			self.logger.warning (
				"Cannot resolve dependencies, no resolver available!"
			)
			return True

		desc = self.package_info ['desc_data']
		self._channels = dict()

		dep_type = desc_field = None

		for dep_type in FIELDS_TO_EVAR:
			resolver = None

			for desc_field in FIELDS_TO_EVAR [dep_type]:
				if desc_field in desc:
					if not resolver:
						resolver = self._get_channel ( dep_type )

					resolver.add_dependencies (
						dep_list     = desc [desc_field],
						deptype_mask = FIELDS [desc_field]
					)
		# -- for dep_type
	# --- end of _init_channels (...) ---

	def _close_channels ( self ):
		"""Closes the resolver channels."""
		if self._channels is None: return

		for channel in self._channels.values(): channel.close()
		del self._channels

		self._channels = None
	# --- end of _close_channels (...) ---

	def _wait_resolve ( self ):
		"""Wait for dep resolution."""
		# True if no channels
		for c in self._channels.values():
			if c.satisfy_request() is None:
				return False
		return True
	# --- end of _wait_resolve (...) ---

	def _make_result ( self ):
		"""Make evars using the depres result."""
		def dep_allowed ( dep ):
			#FIXME hardcoded

			# the oldest version of dev-lang/R in portage
			OLDEST_R_VERSION = ( 2, 20, 1 )

			if not dep:
				return False

			cat, sep, remainder = dep.partition ( '/' )

			if not sep:
				raise Exception ( "bad dependency string '%s'!" % dep )

			dep_list = remainder.split ( '-', 2 )

			if len ( dep_list ) < 2:
				ver = ( 0, )
			else:
				ver = tuple ( int (x) for x in dep_list [1].split ( '.' ) )


			if cat.endswith ( 'dev-lang' ) \
				and dep_list [0] == 'R' \
				and cat [0] != '!' \
			:
				if not ver:
					# filters out 'dev-lang/R'
					return False
				else:
					return ver > OLDEST_R_VERSION

			return True
		# --- end of dep_allowed (...) ---

		# RDEPEND -> <deps>, DEPEND -> <deps>, ..
		_depmap = dict()
		# two for dep_type, <sth> loops to safely determine the actual deps
		# (e.g. whether to include R_SUGGESTS in RDEPEND)
		for dep_type, channel in self._channels.items():
			deplist = tuple ( filter (
				dep_allowed, channel.collect_dependencies() )
			)

			if len ( deplist ) > 0:
				self.logger.debug ( "adding %s to %s", deplist, dep_type )
				_depmap [dep_type] = deplist
			# else: (effectively) no dependencies for dep_type


		self._close_channels()

		self.has_suggests = bool ( 'R_SUGGESTS' in _depmap )

		_result = list()
		for dep_type, deps in _depmap.items():
			# add dependencies in no_append/override mode
			_result.append (
				EBUILDVARS [dep_type] (
					deplist,
					using_suggests=self.has_suggests
				)
			)

		if self.create_iuse:
			_result.append ( evars.IUSE ( using_suggests=self.has_suggests ) )

		self.result = tuple ( _result )
	# --- end of _make_result (...) ---
