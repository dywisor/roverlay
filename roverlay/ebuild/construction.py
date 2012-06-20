# R Overlay -- ebuild creation, ebuild class
# Copyright 2006-2012 Gentoo Foundation
# Distributed under the terms of the GNU General Public License v2

import copy

import roverlay.config

from roverlay.util   import shorten_str
from roverlay.ebuild import Ebuild

EBUILD_INDENT = roverlay.config.get ( 'EBUILD.indent', '\t' )

ADD_REMAP = {
	# pkg vs package
	'package_name'     : 'pkg_name',
	'package_version'  : 'pkg_version',
	'package_revision' : 'pkg_revision',
	# TITLE is in DESCRIPTION
	'TITLE'            : 'DESCRIPTION',

	# TODO: remove these entries by fixing ebuildcreator/ebuildjob
	'DEPENDS'          : 'DEPEND',
	'RDEPENDS'         : 'RDEPEND',
	'RSUGGESTS'        : 'R_SUGGESTS',
}

IUSE_SUGGESTS = "R_suggests"


class EbuildConstruction ( object ):
	"""Class that helps to create Ebuild objects."""



	def __init__ ( self, logger ):
		"""Initializes an EbuildConstruction object.

		arguments:
		* logger --
		"""
		self.logger = logger

		self.has_rsuggests = False

		# elements in data are either a str or a list of str
		self._data = dict ()
	# --- end of __init__ (...) ---

	def get_ebuild ( self ):
		"""Creates and returns an Ebuild."""
		lines = '\n'.join ( self._make_ebuild_lines() )
		return Ebuild ( lines, header=None )
	# --- end of get_ebuild (...) ---

	def add ( self, key, value, append=True ):
		"""Adds data.

		arguments:
		* key    -- identifier of the data (e.g. DEPEND).
		             May be remapped (e.g. merging 'Title' and 'Description')
		             or even refused here.
		* value  --
		* append -- whether to append values or overwrite existing ones,
		            defaults to True.

		returns: None (implicit)
		"""
		if self._data is None:
			# -- todo
			raise Exception ("Ebuild is readonly.")

		_key = ADD_REMAP [key] if key in ADD_REMAP else key

		if _key is None:
			self.logger.debug ( "add (%s, %s): filtered key.", key, value )
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

	def _make_ebuild_lines ( self ):
		"""Creates text lines for the Ebuild.
		It assumes that enough data to do this are available.
		Exceptions (KeyError, NameError, ...) are passed if that's not the case.
		"""

		def get_dep_and_use():
			"""Creates values for the DEPEND, RDEPEND, IUSE and, if possible,
			R_SUGGESTS variables and returns them as dict { VARNAME -> VALUE }.
			"""

			# have suggests if they're set and not empty
			self.has_rsuggests = bool (
				'R_SUGGESTS' in self._data and self._data ['R_SUGGESTS']
			)

			# set defaults: inherit eclass + include depend in rdepend
			# TODO: is ${DEPEND:-},... necessary?
			ret = dict (
				DEPEND  = [ '${DEPEND:-}' ],
				# assuming that the eclass includes it's DEPEND in RDEPEND
				RDEPEND = [ '${RDEPEND:-}' ],
				IUSE    = [ '${IUSE:-}' ],
			)

			for kw in ( x for x in ( 'DEPEND', 'RDEPEND' ) if x in self._data ):
				if isinstance ( self._data [kw], list ):
					ret [kw].extend ( self._data [kw] )
				else:
					ret [kw].append ( self._data [kw] )


			if self.has_rsuggests:
				ret ['R_SUGGESTS'] = self._data ['R_SUGGESTS']

				# +R_SUGGESTS, -R_SUGGESTS?
				ret ['IUSE'].append ( IUSE_SUGGESTS )
				# do these braces help or confuse? TODO FIXME
				ret ['RDEPEND'].append ( '%s? ( ${R_SUGGESTS} )' % IUSE_SUGGESTS )

			return ret

		# --- end of get_dep_and_use () ---

		def make_var (
			varname,
			value=None, oneline_list=True, indent_list=True, indent_level=0
		):
			"""Creates a <name>=<value> statement for ebuilds.

			arguments:
			* varname      -- name of the variable
			* value        -- value of the variable.
			                   This has to be either None (the default), str,
			                   or list of str.
			* oneline_list -- if value is a list: controls whether its components
			                   should be put into one line (True) or multiple.
			                   Defaults to True.
			* indent_list  -- if value is a list and not oneline_list:
			                   controls whether each value line should be
			                   indentend (by indent_level + 1) or not ("by 0").
			                   Defaults to True.
			* indent_level -- current indentation level, defaults to 0

			"""

			# assumption: value is either None,
			#              scalar with str representation or list of str
			var_value = None

			if not value:
				var_value = ""

			elif isinstance ( value, list ):
				if oneline_list:
					var_value = ' '.join ( value )
				elif indent_list:
					var_value = (
						'\n' + (indent_level + 1) * EBUILD_INDENT
					).join ( value )
				else:
					'\n'.join ( value )

			else:
				var_value = str ( value )


			# (TODO)
			# fixing ebuild var values here

			# cut DESCRIPTION line if too long
			if varname == 'DESCRIPTION':
				var_value = shorten_str ( var_value, 45, '... (see metadata)' )


			ret ='%s%s="%s"' % (
				indent_level * EBUILD_INDENT,
				varname,
				var_value
			)

			# (TODO)
			# fixing ebuild var lines here

			return ret

		# --- end of make_var (...) ---

		def remove_newlines ( line_list ):
			"""Removes leading, ending and repeated blank lines in line_list.

			arguments:
			* line_list --

			returns: filtered lines

			TODO: check if a filter function could be used for this
			"""
			lines = []
			line = None
			last_line_empty = True

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

		def add_easyvar (
			ebuild_content, varname,
			value_key=None, add_newline=False
		):
			"""Adds a 'simple' variable to the ebuild lines.
			This means that it can directly be taken from self._data [value_key].
			This method assumes that value_key exists in self._data,
			any exceptions (KeyError) will be passed.

			arguments:
			* ebuild_content -- list of ebuild text lines, will be modified
			                     directly, so copy it before calling addvar if
			                     you need the original list.
			* varname        -- name of the variable.
			                     Nothing happens if this is None.
			* value_key      -- key of the value,
			                     defaults to varname if it is None
			* add_newline    -- adds a newline after the var statement,
			                     defaults to False

			returns: given+modified list (ebuild_content)
			"""

			if not varname is None:
				if value_key is None:
					ebuild_content.append (
						make_var ( varname, self._data [varname] )
					)
				else:
					ebuild_content.append (
						make_var ( varname, self._data [value_key] )
					)

				if add_newline:
					ebuild_content.append ( "" )

			return ebuild_content

		# --- end of add_easyvar (...) ---

		# -- actual start of _make_ebuild_lines (...) --
		try:
			ebuild_lines = []

			#if 'ebuild_header' in self._data:
			#	ebuild_lines = copy.copy ( self._data ['ebuild_header'] )
			#	ebuild_lines.append ( "" )

			#add_easyvar ( ebuild_lines, "PKG_FILE" )
			#if 'PKG_ORIGIN' in self._data:
			#	add_easyvar ( ebuild_lines, "PKG_ORIGIN", None, False )

			ebuild_lines.append ( "" )

			# TODO/FIXME: this makes DESCRIPTION mandatory, maybe check with
			#  >if 'DESCRIPTION' in self._data<
			add_easyvar ( ebuild_lines, "DESCRIPTION" )

			add_easyvar ( ebuild_lines, "SRC_URI", add_newline=True )

			# FIXME/TODO: LICENSE?

			dep_and_use = get_dep_and_use ()

			# check that IUSE has more than one element,
			#  don't write IUSE="${IUSE:-}" etc.
			if len ( dep_and_use ['IUSE'] ) > 1:
				ebuild_lines.append (
					make_var ( "IUSE", dep_and_use ['IUSE'], True )
				)

			if 'R_SUGGESTS' in dep_and_use:
				ebuild_lines.append (
					make_var ( "R_SUGGESTS", dep_and_use ['R_SUGGESTS'], False )
				)

			# see IUSE
			if len ( dep_and_use ['DEPEND'] ) > 1:
				ebuild_lines.append (
					make_var ( "DEPEND", dep_and_use ['DEPEND'], False )
				)

			# see IUSE
			if len ( dep_and_use ['RDEPEND'] ) > 1:
				ebuild_lines.append (
					make_var ( "RDEPEND", dep_and_use ['RDEPEND'], False )
				)

			del dep_and_use
			return remove_newlines ( ebuild_lines )

		except ( ValueError, KeyError, NameError ) as err:
			#self.logger.exception ( err )
			self.logger.error ( "Cannot create ebuild text lines." )
			#return None
			raise

		# --- end of make_ebuild_lines (...) ---
