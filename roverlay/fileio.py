# R Overlay -- file in/out
# Copyright 2006-2012 Gentoo Foundation
# Distributed under the terms of the GNU General Public License v2

import re
import os.path
import tarfile

# temporary import until logging is implemented
from sys import stderr as logging



# temporary import until config and real constants are implemented
from roverlay import tmpconst as const

class DescriptionReader:

	@classmethod
	def __init__ ( self ):
		"""Initializes a DESCRIPTION file reader."""
		self._mandatory_fields = []

	@classmethod
	def _get_mandatory_fields ( self, force_update=False ):
		"""Returns a list of the fields a DESCRIPTION file must define.

		arguments:
		* force_update -- enforce creation of a new list
		"""

		# use previously calculated results (if item count > 0)
		if force_update or ( not len (self._mandatory_fields) ):
			field = None
			mandatory = []
			for field in const.DESCRIPTION_FIELD_MAP.keys():
				if 'flags' in const.DESCRIPTION_FIELD_MAP [field]:
					if 'mandatory' in const.DESCRIPTION_FIELD_MAP [field] ['flags']:
						mandatory.append ( field )

			self._mandatory_fields = mandatory
			del field, mandatory

		return self._mandatory_fields

	@classmethod
	def _find_field ( self , field_identifier ):
		"""Determines the real name of a field.

		arguments:
		* field_identifier -- name of the field as it appears in the DESCRIPTION file

		At first, it is checked whether field_identifier matches the name of
		a field listed in DESCRIPTION_FIELD_MAP (any match results in immediate return).
		Then, a new iteration over the field map compares field_identifier
		with all aliases until the first case-(in)sensitive match (-> immediate return).
		An emptry string will be returned if none of the above searches succeed.

		In other words: this method decides whether a field_identifier will be used and if so,
		with which name.
		"""

		# save some time by prevent searching if field_id is empty
		if not field_identifier:
			return ''

		# search for real field names first
		for field in const.DESCRIPTION_FIELD_MAP.keys():
			if field_identifier == field:
				return field

		field_id_lower = field_identifier.lower()

		for field in const.DESCRIPTION_FIELD_MAP.keys():

			# ?TODO : DESCRIPTION_FIELD_MAP ['alias'] [<alias_types>] instead of the current structure?

			# does extra information (-> alias(es)) for this field exist?
			if isinstance ( const.DESCRIPTION_FIELD_MAP [field], dict ):

				for alias_type in const.DESCRIPTION_FIELD_MAP [field] . keys():

					if alias_type == 'withcase':

						for alias in const.DESCRIPTION_FIELD_MAP [field] [alias_type]:
							if field_identifier == alias:
								return field

					elif alias_type == 'nocase':

						for alias in const.DESCRIPTION_FIELD_MAP [field] [alias_type]:
							if field_id_lower == alias.lower():
								return field

					#elif other_alias_type:

		# returning empty string if no valid field identifier matches
		return ''

	@classmethod
	def _make_values ( self, value_str, field_context=None ):
		"""Extracts relevant data from value_str and returns them as list.

		arguments:
		* value_str -- string that represents the (just read) values
		* field_context -- field name the value belongs to; optional, defaults to None

		It's useful to set field_context 'cause several fields ('Depends') have
		multiple values arranged in a list (dep0, dep1 [, depK]*).
		"""

		svalue_str = value_str.strip()

		if field_context is None:
			# default return if no context given
			return [ svalue_str ]

		if self._check_fieldflag ( field_context ):
			# have flags for field_context, check these

			if self._check_fieldflag ( field_context, 'isList' ):
					# split up this list (that is separated by commata and/or semicolons)
					return re.split (const.DESCRIPTION_LIST_SPLIT_REGEX, svalue_str, 0)

			elif self._check_fieldflag ( field_context, 'isWhitespaceList' ):
					# split up this list (that is separated whitespace)
					return re.split ( '\s+', svalue_str, 0 )


		# default return
		return [ svalue_str ]

	@classmethod
	def _check_fieldflag ( self, field, flag_to_check=None ):
		"""Checks if the given field has the specified flag and returns a bool.

		arguments:
		* field -- name of the field that should be checked
		* flag_to_check -- name of the flag to check; optional, defaults to None

		This method acts as 'field has any flags?' if flag_to_check is None (it's default value).
		"""

		if field in const.DESCRIPTION_FIELD_MAP:

			if 'flags' in const.DESCRIPTION_FIELD_MAP [field]:

				if flag_to_check in const.DESCRIPTION_FIELD_MAP [field] ['flags']:
					return True

				elif flag_to_check is None:
					# 'flags' exist, return true
					return True

		return False

	@staticmethod
	def _get_desc_from_tarball ( tarball, pkg_name='.' ):
		"""
		Extracts the contents of the description file in the given tarball
		and returns them as list of str.

		arguments:
		* tarball -- tarball to read
		* pkg_name -- name of the package, usually the description file is
		               <pkg_name>/DESCRIPTION and this that arguments is
		               required. Defaults to '.', set to None to disable.

		All exceptions are passed to the caller (TarError, IOErr, <custom>).
		"""

		logging.write ( "Starting to read tarball file '" + tarball + "' ...\n" )

		if not tarfile.is_tarfile ( tarball ):
			# not a tarball, <todo> real exception
			raise Exception ("tarball expected")

		# open a file handle <fh> for the DESCRIPTION file using a tar handle <th>
		th = fh = None

		th = tarfile.open ( tarball, 'r' )
		if pkg_name:
			fh = th.extractfile (
				os.path.join ( pkg_name, const.DESCRIPTION_FILE_NAME )
			)
		else:
			fh = th.extractfile ( const.DESCRIPTION_FILE_NAME )

		x = None
		# get lines from <fh>, decode and remove end of line whitespace
		read_lines = [ x.decode().rstrip() for x in fh.readlines() ]
		del x

		fh.close()
		th.close()

		del fh, th
		return read_lines



	@classmethod
	def readfile ( self, file ):
		"""Reads a DESCRIPTION file and returns the read data if successful, else None.

		arguments:
		* file -- path to the tarball file (containing the description file)
		          that should be read

		It does some pre-parsing, inter alia
		-> assigning field identifiers from the file to real field names
		-> split field values
		-> filter out unwanted/useless fields

		The return value is a dict "<field name> => <field value[s]>"
		with <field value> as str and <field values> as list.
		"""

		# todo move that regex to const
		filename = re.sub ('[.](tgz|tbz2|(tar[.](gz|bz2)))',
			'',
			os.path.basename ( file )
		)
		# todo move that separator to const
		package_name, sepa, package_version = filename.partition ( '_' )
		if not sepa:
			# file name unexpected
			raise Exception ("file name unexpected")


		try:
			desc_lines = DescriptionReader._get_desc_from_tarball ( file, package_name )

		except IOError as err:
			# <todo>
			raise

		read_data = dict()

		field_context = val = line = sline = None
		for line in desc_lines:
			# using s(tripped)line whenever whitespace doesn't matter
			sline = line.lstrip()

			if not sline:
				# empty line
				pass

			elif line [0] == const.DESCRIPTION_COMMENT_CHAR:
				pass

			elif field_context and line [0] != sline [0]:
				# line starts with whitespace and context is set => append values
				for val in self._make_values ( sline, field_context ):
					read_data [field_context] . append ( val )


			elif line [0] != sline [0]:
				# line starts with whitespace and context is not set => ignore
				pass

			else:
				# new context, forget last one
				field_context = None

				line_components = sline.partition ( const.DESCRIPTION_FIELD_SEPARATOR )


				if line_components [1]:
					# line contains a field separator, set field context
					field_context = self._find_field ( line_components [0] )

					if field_context:
						# create a new empty list for field_context
						read_data [field_context] = []

						if len ( line_components ) == 3:
							# add values to read_data
							for val in self._make_values ( line_components [2], field_context ):
								read_data [field_context] . append ( val )

					else:
						# useless line, skip
						logging.write (
							"Skipping a line, first line component (field identifier?) was: '"
							+ line_components [0] + "'\n"
						)

					del line_components

				else:
					# how to reach this block? -- remove later
					raise Exception ( "should-be unreachable code" )

		del val, line, sline, field_context

		def stats ( data ):
			"""Temporary function that prints some info about the given data."""
			field = None
			logging.write ( "=== this is the list of read data ===\n" )
			for field in read_data.keys():
				logging.write ( field + " = " + str ( read_data [field] ) + "\n" )
			logging.write ( "=== end of list ===\n" )
			del field

		stats ( read_data )

		# "finalize" data
		field = None
		for field in read_data.keys():
			if self._check_fieldflag ( field ):
				# has flags
				if self._check_fieldflag ( field, 'joinValues' ):
					read_data [field] = ' ' . join ( read_data [field] )

		# verify that all necessary fields have been added and are set
		missing_fields = dict()
		for field in self._get_mandatory_fields():
			if field in read_data:
				if not len (read_data [field]):
					missing_fields [field] = 'unset'

			else:
				missing_fields [field] = 'missing'

		if len (missing_fields):
			logging.write ("Verification of mandatory fields failed, the result leading to this is: " +
				str (missing_fields) + "\n"
			)

			#<raise custom exception>
			raise Exception ("^^^look above")

		del field, missing_fields

		# add default values

		logging.write ( "Fixing data...\n" )
		stats ( read_data )

		return read_data

