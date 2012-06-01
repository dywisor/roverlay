# R Overlay -- ebuild creation, ebuild class
# Copyright 2006-2012 Gentoo Foundation
# Distributed under the terms of the GNU General Public License v2

import roverlay.config

class Ebuild:
	EBUILD_INDENT = roverlay.config.get ( 'EBUILD.indent', '\t' )

	ADD_REMAP = {
		# pkg vs package
		'package_name'     : 'pkg_name',
		'package_version'  : 'pkg_version',
		'package_revision' : 'pkg_revision',
		# TITLE is in DESCRIPTION
		'TITLE'            : 'DESCRIPTION',
	}

	def __init__ ( self, logger ):
		"""Initializes an Ebuild.
		This is an abstraction layer between the verified + calculated data
		and the ebuild data, which can be written into a file / stdout / stdin.
		Most functions here assume that everything is fine when it reaches them.

		arguments:
		* logger -- logger for this Ebuild
		"""

		self.logger = logger

		# elements in ebuild_data are either a str or a list of str
		self._data = dict ()
		self._ebuild_lines = None
		self._ebuild_name = None

	# --- end of __init__ (...) ---

	def cleanup ( self ):
		"""Removes stored data if ebuild_lines have already been calculated.
		This saves some memory but makes this Ebuild read-only.
		"""
		if self._ebuild_lines:
			# determine the ebuild name first
			self._ebuild_name = self.suggest_name()
			del self._data
			self._data = None

	# --- end of cleanup (...) ---

	def prepare ( self, force_update=False, cleanup_after=False ):
		"""Tells this Ebuild to create ebuild lines.

		arguments:
		* force_update -- create ebuild lines if they exist; defaults to False
								and ignored if this Ebuild has been cleaned up
		* cleanup_after -- run cleanup() after successful creation

		Returns True if ebuild_lines have been created or if they exist and
		an update has not been enforced. Else returns False.
		"""
		if self._ebuild_lines and not force_update:
			return True
		elif self._data:
			self._ebuild_lines = self._make_ebuild_lines()
			if self._ebuild_lines:
				if cleanup_after: self.cleanup()
				return True
		elif self._ebuild_lines:
			# self._data is None
			return True


		return False

	# --- end of prepare (...) ---

	def has_ebuild ( self ):
		"""Returns True if this object has ebuild text lines else False."""
		return bool ( self._ebuild_lines )
	# --- end of has_ebuild (...) ---

	def add ( self, key, value, append=True ):
		"""Adds data to this Ebuild.

		arguments:
		* key -- identifier of the data (e.g. DEPEND).
		         May be remapped (e.g. merging 'Title' and 'Description')
		         or even refused here
		* value --
		* append -- whether to append values or overwrite existing ones,
		            defaults to True.

		raises: Exception when ebuild data are readonly
		"""
		if self._data is None:
			# -- todo
			raise Exception ("Ebuild data are readonly.")

		_key = Ebuild.ADD_REMAP [key] if key in Ebuild.ADD_REMAP else key

		if _key is None:
			self.logger.debug ( "add (%s, %s): filtered key.", key, str ( value ) )
		else:
			if append and _key in self._data:
				if not isinstance ( self._data [_key], list ):
					self._data [_key] = [ self._data [_key] ]

				if isinstance ( value, list ):
					self._data [_key].extend ( value )
				else:
					self._data [_key].append ( value )

			else:
				self._data [_key] = value

	# --- end of add (...) ---

	def write ( self, file_to_write ):
		"""Writes an ebuild file.

		arguments:
		* file_to_write -- path to the file that should be written
		"""
		# prepare ebuild lines and open file handle after that
		if self.prepare ( False, False ):
			try:
				fh = open ( file_to_write, 'w' )
				self.show ( fh )
				fh.close()
				del fh
			except IOError as err:
				self.logger.exception ( err )
				raise

		else:
				self.logger.warning ( "Cannot write ebuild - it's empty! (check with has_ebuild() before calling this method.)" )

	# --- end of write (...) ---

	def show ( self, file_handle ):
		"""Prints the ebuild content into a file_handle.

		arguments:
		file_handle -- object that has a writelines ( list ) method, e.g. file.

		Returns True if writing was successful, else False.
		"""
		if self.prepare ( False, False ):
			lines = [ line + "\n" for line in self._ebuild_lines ]
			file_handle.writelines ( lines )
			del lines
			return True
		else:
			return False

	# --- end of show (...) ---

	def suggest_dir_name ( self ):
		"""Suggests a direcory name for this Ebuild."""
		return self._data ['pkg_name'] if 'pkg_name' in self._data else self.suggest_name().partition ( '-' )
	# --- end of suggest_dir_name (...) ---

	def suggest_name ( self, fallback_name='' ):
		"""Suggests a file name for the ebuild. This is calculated using
		pkg_name/version/revision. Returns a fallback_name if this is not
		possible.

		arguments:
		fallback_name -- name to return if no suggestion available, defaults to empty string
		"""

		if self._ebuild_name:
			return self._ebuild_name
		elif (not self._data is None) and 'pkg_name' in self._data:
			name_components = [ self._data ['pkg_name'] ]

			if 'pkg_version' in self._data:
				name_components.append ( self._data ['pkg_version'] )
			else:
				# default ver
				name_components.append ( '1.0' )

			if 'pkg_revision' in self._data:
				rev = self._data ['pkg_revision']

				# omit rev == 0 and invalid revisions
				if isinstance ( rev, int ) and rev > 0:
					name_components.append ( 'r' + rev )

			return '-'.join ( name_components )

		else:
			return fallback_name

	# --- end of suggest_name (...) ---

	def _make_ebuild_lines ( self ):
		"""Creates text lines for this Ebuild.
		It assumes that enough data to do this are available. Exceptions (KeyError, NameError, ...)
		are passed if that's not the case.
		"""

		def get_dep_and_use():
			"""Creates values for the DEPEND, RDEPEND, IUSE and, if possible,
			R_SUGGESTS variables and returns them as dict { VARNAME -> VALUE }.
			"""

			# have suggests if they're set and not empty
			have_suggests = bool ( 'RSUGGESTS' in self._data and self._data ['RSUGGESTS'] )

			# set defaults: inherit eclass + include depend in rdepend
			# TODO: is ${DEPEND:-},... necessary?
			ret = dict (
				DEPEND  = [ '${DEPEND:-}' ],
				# RDEPEND: assuming that the eclass includes it's DEPEND in RDEPEND
				RDEPEND = [ '${RDEPEND:-}' ],
				IUSE    = [ '${IUSE:-}' ],
			)

			tmp = None

			if 'DEPEND' in self._data:
				# todo: search if there is a extend method that does not split string into chars
				tmp = self._data ['DEPEND']
				if isinstance ( tmp, list ):
					ret ['DEPEND'].extend ( tmp )
				else:
					ret ['DEPEND'].append ( tmp )

			if 'RDEPEND' in self._data:
				tmp = self._data ['RDEPEND']
				if isinstance ( tmp, list ):
					ret ['RDEPEND'].extend ( tmp )
				else:
					ret ['RDEPEND'].append ( tmp )

			if have_suggests:
				ret ['R_SUGGESTS'] = self._data ['R_SUGGESTS']

				# +R_SUGGESTS, -R_SUGGESTS?
				ret ['IUSE'].append ( 'R_suggests' )
				# do these braces help or confuse? TODO FIXME
				ret ['RDEPEND'].append ( '( R_suggests ? ${R_SUGGESTS} )' )

			return ret

		# --- end of get_dep_and_use () ---

		def make_var ( varname, value=None, oneline_list=True, indent_list=True, indent_level=0 ):
			"""Creates a <name>=<value> statement for ebuilds.

			arguments:
			* varname -- name of the variable
			* value -- value of the variable. This has to be either None (the default),
			           str, or list of str.
			* oneline_list -- if value is a list: controls whether its components should be
			                  put into one line (True) or multiple (False). Defaults to True.
			* indent_list -- if value is a list and not oneline_list:
			                 controls whether each value line should be indentend
			                 (by indent_level + 1) or not ("by 0"). Defaults to True.
			* indent_level -- current indentation level, defaults to 0

			"""

			# assumption: value is either None, scalar with str representation or list of str
			var_value = None

			if not value:
				var_value = ""

			elif isinstance ( value, list ):
				if oneline_list:
					var_value = ' '.join ( value )
				elif indent_list:
					var_value = ('\n' + (indent_level + 1) * Ebuild.EBUILD_INDENT).join ( value )
				else:
					'\n'.join ( value )

			else:
				var_value = str ( value )

			return indent_level * Ebuild.EBUILD_INDENT + varname + '="' + var_value + '"'

		# --- end of make_var (...) ---

		def remove_newlines ( line_list ):
			"""
			Removes leading, ending and repeated empty/whitespace lines in line_list.

			arguments:
			* line_list
			"""
			lines = []
			line = None
			last_line_empty = False

			for line in line_list:
				line = line.rstrip()
				# re.sub \n{2,} \n :: FIXME?

				if line:
					last_line_empty = False
				elif not last_line_empty:
					last_line_empty = True
				else:
					continue

				lines.append ( line )

			# remove last line if empty
			##if last_line_empty: (?)
			if len ( lines ) and not lines [-1]:
				del lines [-1]

			return lines

		# --- end of remove_newlines (...) ---

		def add_easyvar ( ebuild_content, varname, value_key=None, add_newline=False):
			"""Adds a 'simple' variable to the ebuild lines. This means that it
			can directly be taken from self._data [value_key]. This method assumes
			that value_key exists in self._data, any exceptions (KeyError) will be passed.

			arguments:
			* ebuild_content -- list of ebuild text lines, will be modified directly,
			                     so copy it before calling addvar if you need the original list.
			* varname -- name of the variable. Nothing happens if this is None.
			* value_key -- key of the value, defaults to varname if it is None
			* add_newline -- adds a newline after the var statement, defaults to False

			Returns given list (ebuild_content), which will then have been modified.
			"""

			if not varname is None:
				if value_key is None:
					ebuild_content.append ( make_var ( varname, self._data [varname] ) )
				else:
					ebuild_content.append ( make_var ( varname, self._data [value_key] ) )

				if add_newline:
					ebuild_content.append ( "" )

			return ebuild_content

		# --- end of add_easyvar (...) ---

		try:
			ebuild_lines = []

			if 'ebuild_header' in self._data:
				ebuild_lines = self._data ['ebuild_header']
				ebuild_lines.append ( "" )

			add_easyvar ( ebuild_lines, "PKG_FILE" )
			if 'PKG_ORIGIN' in self._data:
				add_easyvar ( ebuild_lines, "PKG_ORIGIN", None, False )

			ebuild_lines.append ( "" )

			add_easyvar ( ebuild_lines, "DESCRIPTION" )

			if 'SRC_URI' in self._data:
				add_easyvar ( ebuild_lines, "SRC_URI" )
			else:
				# > calculate SRC_URI using self._data ['origin'] -- either here or in eclass
				ebuild_lines.append ( make_var ( "SRC_URI" , None ) )
				# (temporary, todo) setting restrict to fetch
				ebuild_lines.append ( make_var ( "RESTRICT" , "fetch" ) )

			ebuild_lines.append ( "" )

			# LICENSE ?

			dep_and_use = get_dep_and_use ()

			# check that IUSE has more than one element, don't write IUSE="${IUSE:-}" etc.
			if len ( dep_and_use ['IUSE'] ) > 1:
				ebuild_lines.append ( make_var ( "IUSE", dep_and_use ['IUSE'], True ) )

			if 'R_SUGGESTS' in dep_and_use:
				ebuild_lines.append ( make_var ( "R_SUGGESTS", dep_and_use ['R_SUGGESTS'], False ) )

			# see IUSE
			if len ( dep_and_use ['DEPEND'] ) > 1:
				ebuild_lines.append ( make_var ( "DEPEND", dep_and_use ['DEPEND'], False ) )

			# see IUSE
			if len ( dep_and_use ['RDEPEND'] ) > 1:
				ebuild_lines.append ( make_var ( "RDEPEND", dep_and_use ['RDEPEND'], False ) )

			del dep_and_use
			return remove_newlines ( ebuild_lines )

		except ( ValueError, KeyError, NameError ) as err:
			self.logger.error ( "Cannot create ebuild text lines. The error message was %s.", str ( err ) )
			return None

		# --- end of make_ebuild_lines (...) ---
