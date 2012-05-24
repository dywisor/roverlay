# R Overlay -- file in/out
# Copyright 2006-2012 Gentoo Foundation
# Distributed under the terms of the GNU General Public License v2

import re

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
	def _get_mandatory_fields ( self ):
		"""Returns a list of the fields a DESCRIPTION file must define."""

		# use previously calculated results (if item count > 0)
		if len (self._mandatory_fields) == 0:
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


		field_id_lower = field_identifier.lower()

		# save some time by prevent searching if field_id is whitespace only/empty
		if not field_id_lower:
			return ''

		# search for real field names first
		for field in const.DESCRIPTION_FIELD_MAP.keys():
			if field_identifier == field:
				return field


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

		if field_context == None:
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

				elif flag_to_check == None:
					# 'flags' exist, return true
					return True

		return False


	@classmethod
	def readfile ( self, file ):
		"""Reads a DESCRIPTION file and returns the read data if successful, else None.

		arguments:
		* file -- path of the file that should be read

		It does some pre-parsing, inter alia
		-> assigning field identifiers from the file to real field names
		-> split field values
		-> filter out unwanted/useless fields

		The return value is a dict "<field name> => <field value[s]>"
		with <field value> as str and <field values> as list.
		"""

		logging.write ( "Starting to read file '" + file + "' ...\n" )

		try:
			fh = open ( file, 'rU' )

			field_context = ''

			read_data = dict()

			val = line = sline = None
			for line in fh:
				# end of line whitespace doesn't matter
				line = line.rstrip()

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
					field_context = ''

					line_components = sline.split (
						const.DESCRIPTION_FIELD_SEPARATOR,
						1
					)

					if len ( line_components ) >= 1:
						# set field context
						field_context = self._find_field ( line_components [0] )

						if field_context:
							# create a new empty list for field_context
							read_data [field_context] = []

							if len ( line_components ) == 2:
								# add values to read_data
								for val in self._make_values ( line_components [1], field_context ):
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

			fh.close()
			del fh, val, line, sline, field_context

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

			del missing_fields

			# add default values

			logging.write ( "Fixing data...\n" )
			stats ( read_data )

			return read_data


		except IOError as err:
			raise

		return None

