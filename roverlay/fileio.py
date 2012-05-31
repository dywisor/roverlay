# R Overlay -- file in/out
# Copyright 2006-2012 Gentoo Foundation
# Distributed under the terms of the GNU General Public License v2

import re
import tarfile
import logging
import os.path


# temporary import until config and real constants are implemented
from roverlay import tmpconst as const

class DescriptionReader:
	"""Description Reader"""

	LOGGER = logging.getLogger ( 'DescriptionReader' )

	def __init__ ( self, package_file, read_now=False ):
		"""Initializes a DESCRIPTION file reader."""

		self.fileinfo  = self.make_fileinfo ( package_file )
		self.logger    = DescriptionReader.LOGGER.getChild ( self.get_log_name() )
		self.desc_data = None


		if read_now:
			self.run()

	# --- end of __init__ (...) ---

	def get_log_name ( self ):
		try:
			return self.fileinfo ['filename']
		except Exception as any_exception:
			return '__undef__'

	def get_desc ( self, run_if_unset=True ):
		if self.desc_data is None:
			self.run ()

		return self.desc_data
	# --- end of get_desc (...) ---

	def get_fileinfo ( self ):
		return self.fileinfo
	# --- end of get_fileinfo (...) ---

	def make_fileinfo ( self, filepath ):
		"""Returns some info about the given filepath as dict whose contents are
			the file path, the file name ([as package_file with suffix and]
			as filename with tarball suffix removed), the package name
			and the package_version.

		arguments:
		* filepath --
		"""

		package_file = os.path.basename ( filepath )

		filename = re.sub ( const.RPACKAGE_SUFFIX_REGEX + '$', '', package_file )

		# todo move that separator to const
		package_name, sepa, package_version = filename.partition ( '_' )

		if not sepa:
			# file name unexpected, tarball extraction will (probably) fail
			DescriptionReader.LOGGER.error ( "unexpected file name %s.'", filename )

		return dict (
			filepath        = filepath,
			filename        = filename,
			package_file    = package_file,
			package_name    = package_name,
			#package_origin = ?,
			package_version = package_version,
		)

	# --- end of make_fileinfo (...) ---


	def _parse_read_data ( self, read_data ):
		"""Verifies and parses/fixes read data.

		arguments:
		* read_data -- data from file, will be modified
		"""

		def get_fields_with_flag ( flag, foce_update=False ):

			matching_fields = []

			field = None
			for field in const.DESCRIPTION_FIELD_MAP.keys():
				if flag is None:
					matching_fields.append ( field )

				elif 'flags' in const.DESCRIPTION_FIELD_MAP [field]:
					if flag in const.DESCRIPTION_FIELD_MAP [field] ['flags']:
						matching_fields.append ( field )

			del field
			return matching_fields

		# --- end of get_fields_with_flag (...) ---

		def value_in_strlist ( _val, _list, case_insensitive=True ):
			"""Returns true if value is in the given list."""
			el = None
			if case_insensitive:
				lowval = _val.lower()
				for el in _list:
					if el.lower() == lowval:
						return True
				del lowval
			else:
				for el in _list:
					if el == _val:
						return True

			del el
			return False
		# --- end of value_in_strlist (...) ---

		field = None

		# insert default values
		for field in const.DESCRIPTION_FIELD_MAP.keys():
			if not field in read_data and 'default_value' in const.DESCRIPTION_FIELD_MAP [field]:
				read_data [field] = const.DESCRIPTION_FIELD_MAP [field] ['default_value']

		# join values to a single string
		for field in get_fields_with_flag ( 'joinValues' ):
			if field in read_data.keys():
				read_data [field] = ' ' . join ( read_data [field] )

		# ensure that all mandatory fields are set
		missing_fields = list()

		for field in get_fields_with_flag ( 'mandatory' ):
			if field in read_data:
				if not len (read_data [field]):
					missing_fields.append ( field )
			else:
				missing_fields.append ( field )




		# check for fields that allow only certain values
		unsuitable_fields = dict()

		for field in read_data.keys():
			if 'allowed_values' in const.DESCRIPTION_FIELD_MAP [field]:
				if not value_in_strlist (
							read_data [field],
							const.DESCRIPTION_FIELD_MAP [field] ['allowed_values']
						):
					unsuitable_fields.append [field] = read_data [field]

		del field

		valid = not bool ( len ( missing_fields ) or len ( unsuitable_fields ) )
		if not valid:
			self.logger.info ( "Cannot use R package" ) # name?
			if len ( missing_fields ):
				self.logger.debug ( "The following mandatory description fields are missing: %s.", str ( missing_fields ) )
			if len ( unsuitable_fields ):
				self.logger.debug ( "The following fields have unsuitable values: %s.", str ( unsuitable_fields ) )

		return valid

	# --- end of _parse_read_data (...) ---

	def run ( self ):
		"""Reads a DESCRIPTION file and returns the read data if successful, else None.

		arguments:
		* file -- path to the tarball file (containing the description file)
		          that should be read

		It does some pre-parsing, inter alia
		-> assigning field identifiers from the file to real field names
		-> split field values
		-> filter out unwanted/useless fields

		The return value is a dict { fileinfo , description_data } or None if
		the read data are "useless" (not suited to create an ebuild for it,
		e.g. if OS_TYPE is not unix).
		"""

		def make_values ( value_str, field_context=None ):
			"""Extracts relevant data from value_str and returns them as list.

			arguments:
			* value_str -- string that represents the (just read) values
			* field_context -- field name the value belongs to; optional, defaults to None

			It's useful to set field_context 'cause several fields ('Depends') have
			multiple values arranged in a list (dep0, dep1 [, depK]*).
			"""

			def check_fieldflag ( field, flag_to_check=None ):
				"""Checks if the given field has the specified flag and returns a bool.

				arguments:
				* field -- name of the field that should be checked
				* flag_to_check -- name of the flag to check; optional, defaults to None

				This method acts as 'field has any flags?' if flag_to_check is None (its default value).
				"""

				if field in const.DESCRIPTION_FIELD_MAP:
					if 'flags' in const.DESCRIPTION_FIELD_MAP [field]:
						if flag_to_check in const.DESCRIPTION_FIELD_MAP [field] ['flags']:
							return True
						elif flag_to_check is None:
							# 'flags' exist, return true
							return True

				return False
			# --- end of check_fieldflag (...) ---

			svalue_str = value_str.strip()

			if not svalue_str:
				# empty value(s)
				return []

			elif field_context is None:
				# default return if no context given
				return [ svalue_str ]

			elif check_fieldflag ( field_context ):
				# value str is not empty and have flags for field_context, check these

				if check_fieldflag ( field_context, 'isList' ):
						# split up this list (that is separated by commata and/or semicolons)
						return re.split (const.DESCRIPTION_LIST_SPLIT_REGEX, svalue_str, 0)

				elif check_fieldflag ( field_context, 'isWhitespaceList' ):
						# split up this list (that is separated whitespace)
						return re.split ( '\s+', svalue_str, 0 )


			# default return
			return [ svalue_str ]

		# --- end of make_values (...) ---

		def get_desc_from_file ( filepath, pkg_name='.' ):
			"""Reads a file returns the description data.

			arguments:
			* filepath -- file to read (str; path to tarball or file)
			* pkg_name -- name of the package, in tarballs the description file
							  is located in <pkg_name>/ and thus this argument is required.
							  Defaults to '.', set to None to disable.

			All exceptions are passed to the caller (TarError, IOErr, <custom>).
			<filepath> can either be a tarball in which case the real DESCRIPTION
			file is read (<pkg_name>/DESCRIPTION) or a normal file.
			"""

			self.logger.debug ( "Starting to read file '" + str ( filepath ) + "' ...\n" )

			if not ( isinstance ( filepath, str ) and filepath ):
				raise Exception ( "bad usage" )

			# read describes how to import the lines from a file (e.g. rstrip())
			#  fh, th are file/tar handles
			read = th = fh = None

			if tarfile.is_tarfile ( filepath ):
				# filepath is a tarball, open tar handle + file handle
				th = tarfile.open ( filepath, 'r' )
				if pkg_name:
					fh = th.extractfile ( os.path.join ( pkg_name, const.DESCRIPTION_FILE_NAME ) )
				else:
					fh = th.extractfile ( const.DESCRIPTION_FILE_NAME )

				# have to decode the lines
				read = lambda lines : [ line.decode().rstrip() for line in lines ]
			else:
				# open file handle only
				fh = open ( filepath, 'r' )
				read = lambda lines : [ line.rstrip() for line in lines ]

			x = None
			read_lines = read ( fh.readlines() )
			del x, read

			fh.close()
			if not th is None: th.close()
			del fh, th

			return read_lines

		# --- end of get_desc_from_file (...) ---

		def find_field ( field_identifier ):
			"""Determines the real name of a field.

			arguments:
			* field_identifier -- name of the field as it appears in the DESCRIPTION file

			At first, it is checked whether field_identifier matches the name of
			a field listed in DESCRIPTION_FIELD_MAP (any match results in immediate return).
			Then, a new iteration over the field map compares field_identifier
			with all aliases until the first case-(in)sensitive match (-> immediate return).
			None will be returned if none of the above searches succeed.

			In other words: this method decides whether a field_identifier will be used and if so,
			with which name.
			"""

			# save some time by prevent searching if field_id is empty
			if not field_identifier:
				return None

			# search for real field names first
			for field in const.DESCRIPTION_FIELD_MAP.keys():
				if field_identifier == field:
					return field

			field_id_lower = field_identifier.lower()

			for field in const.DESCRIPTION_FIELD_MAP.keys():

				# does extra information (-> alias(es)) for this field exist?
				if 'alias' in const.DESCRIPTION_FIELD_MAP [field]:

					if 'withcase' in const.DESCRIPTION_FIELD_MAP [field] ['alias']:
						for alias in const.DESCRIPTION_FIELD_MAP [field] ['alias'] ['withcase']:
							if field_identifier == alias:
								return field

					if 'nocase' in const.DESCRIPTION_FIELD_MAP [field] ['alias']:
						for alias in const.DESCRIPTION_FIELD_MAP [field] ['alias'] ['nocase']:
							if field_id_lower == alias.lower():
								return field

					#if 'other_alias_type' in const.DESCRIPTION_FIELD_MAP [field] ['alias']:

			# returning None if no valid field identifier matches
			return None

		# --- end of find_field (...) ---


		self.desc_data = None
		read_data = dict ()


		try:
			desc_lines = get_desc_from_file (
				self.fileinfo ['filepath'],
				self.fileinfo ['package_name']
			)

		except IOError as err:
			self.logger.exception ( err )
			return self.desc_data


		field_context = val = line = sline = None
		for line in desc_lines:

			# using s(tripped)line whenever whitespace doesn't matter
			sline = line.lstrip()

			if (not sline) or (line [0] == const.DESCRIPTION_COMMENT_CHAR):
				# empty line or comment
				pass

			elif line [0] != sline [0]:
				# line starts with whitespace

				if field_context:
					# context is set => append values

					for val in make_values ( sline, field_context ):
						read_data [field_context] . append ( val )
				else:
					# no valid context => ignore line
					pass

			else:
				# line introduces a new field context, forget last one
				field_context = None

				line_components = sline.partition ( const.DESCRIPTION_FIELD_SEPARATOR )

				if line_components [1]:
					# line contains a field separator, set field context
					field_context = find_field ( line_components [0] )

					if field_context:
						# create a new empty list for field_context
						read_data [field_context] = []

						# add values to read_data
						#  no need to check line_components [2] 'cause [1] was a true str
						for val in make_values ( line_components [2], field_context ):
							read_data [field_context] . append ( val )

					else:
						# useless line, skip
						self.logger.info ( "Skipped a description field: '%s'.", line_components [0] )

				else:
					# reaching this branch means that
					#  (a) line has no leading whitespace
					#  (b) line has no separator (:)
					# this should not occur in description files (bad syntax?)
					self.logger.warning ( "Unexpected line in description file: '%s'.", line_components [0] )


				del line_components

		del sline, line, val, field_context


		if self._parse_read_data ( read_data ):
			self.logger.debug ( "Successfully read file '%s' with data = %s.",
										self.fileinfo ['filepath'], str ( read_data )
									)
			self.desc_data = read_data

		# get_desc() is preferred, but this method returns the desc data, too
		return self.desc_data

	# --- end of readfile (...) ---
