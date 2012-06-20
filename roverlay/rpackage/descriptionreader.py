# R Overlay -- description reader
# Copyright 2006-2012 Gentoo Foundation
# Distributed under the terms of the GNU General Public License v2

import re
import tarfile
import logging
import os.path

from roverlay          import config
from roverlay.rpackage import descriptionfields

class DescriptionReader ( object ):
	"""Description Reader"""

	#LOGGER = logging.getLogger ( 'DescriptionReader' )


	def __init__ ( self, package_info, logger, read_now=False ):
		"""Initializes a DESCRIPTION file reader."""

		if not config.access().get_field_definition():
			raise Exception (
				"Field definition is missing, cannot initialize DescriptionReader."
			)

		self.field_definition = config.access().get_field_definition()
		self.fileinfo         = package_info
		self.logger           = logger.getChild ( 'desc_reader' )
		self.desc_data        = None


		if read_now:
			self.run()

	# --- end of __init__ (...) ---

	def get_desc ( self, run_if_unset=True ):
		if self.desc_data is None:
			self.run ()

		return self.desc_data
	# --- end of get_desc (...) ---

	def _parse_read_data ( self, read_data ):
		"""Verifies and parses/fixes read data.

		arguments:
		* read_data -- data from file, will be modified
		"""

		# insert default values
		default_values = self.field_definition.get_fields_with_default_value()
		for field_name in default_values.keys():
			if not field_name in read_data:
				read_data [field_name] = default_values [field_name]


		# join values to a single string
		for field_name in self.field_definition.get_fields_with_flag ( 'joinValues' ):

			if field_name in read_data:
				read_data [field_name] = ' ' . join ( read_data [field_name] )

		# ensure that all mandatory fields are set
		missing_fields = set ()

		for field_name in self.field_definition.get_fields_with_flag ( 'mandatory' ):
			if field_name in read_data:
				if read_data [field_name] is None or len ( read_data [field_name] ) < 1:
					missing_fields.add ( field_name )
				#else: ok
			else:
				missing_fields.add ( field_name )


		# check for fields that allow only certain values
		unsuitable_fields = set()

		restricted_fields = self.field_definition.get_fields_with_allowed_values()
		for field_name in restricted_fields:
			if field_name in read_data:
				if not self.field_definition.get ( field_name ).value_allowed ( read_data [field_name] ):
					unsuitable_fields.add ( field_name )

		# summarize results
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

		The return value is a description_data dict or None if the read data
		are "useless" (not suited to create an ebuild for it,
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

			svalue_str = value_str.strip()

			if not svalue_str:
				# empty value(s)
				return []

			elif field_context is None:
				# default return if no context given
				return [ svalue_str ]

			elif field_context in self.field_definition.get_fields_with_flag ( 'isList' ):
					# split up this list (that is separated by commata and/or semicolons)
					# *beware*/fixme: py3, filter returns filter object
					return filter ( None, re.split (
						config.get ( 'DESCRIPTION.list_split_regex' ),
						svalue_str,
						0
					) )

			elif field_context in self.field_definition.get_fields_with_flag ( 'isWhitespaceList' ):
					# split up this list (that is separated whitespace)
					return filter ( None, re.split ( '\s+', svalue_str, 0 ) )



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
					fh = th.extractfile ( os.path.join (
						pkg_name,
						config.get ( 'DESCRIPTION.file_name' )
						) )
				else:
					fh = th.extractfile ( config.get ( 'DESCRIPTION.file_name' ) )

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

		self.desc_data = None
		read_data = dict ()

		try:
			desc_lines = get_desc_from_file (
				self.fileinfo ['package_file'],
				self.fileinfo ['package_name']
			)

		except IOError as err:
			self.logger.exception ( err )
			return self.desc_data

		field_context = None

		for line in desc_lines:
			field_context_ref = None

			# using s(tripped)line whenever whitespace doesn't matter
			sline = line.lstrip()

			if (not sline) or (line [0] == config.get ( 'DESCRIPTION.comment_char' ) ):
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

				line_components = sline.partition ( config.get ( 'DESCRIPTION.field_separator' ) )

				if line_components [1]:
					# line contains a field separator, set field context
					field_context_ref = self.field_definition.get ( line_components [0] )

					if field_context_ref is None:
						# useless line, skip
						self.logger.info ( "Skipped a description field: '%s'.", line_components [0] )
					elif field_context_ref.has_flag ( 'ignore' ):
						# field ignored
						self.logger.debug ( "Ignored field '%s'.", field_context )

					else:
						field_context = field_context_ref.get_name()

						if not field_context:
							raise Exception ( "Field name is not valid! This should've already been catched in DescriptionField..." )

						# create a new empty list for this field_context
						read_data [field_context] = []

						# add values to read_data
						#  no need to check line_components [2] 'cause [1] was a true str
						for val in make_values ( line_components [2], field_context ):
							read_data [field_context] . append ( val )



				else:
					# reaching this branch means that
					#  (a) line has no leading whitespace
					#  (b) line has no separator (:)
					# this should not occur in description files (bad syntax?)
					self.logger.warning ( "Unexpected line in description file: '%s'.", line_components [0] )

		# -- end for --

		if self._parse_read_data ( read_data ):
			self.logger.debug ( "Successfully read file '%s' with data = %s.",
										self.fileinfo ['package_file'], str ( read_data )
									)
			self.desc_data = read_data

		# get_desc() is preferred, but this method returns the desc data, too
		return self.desc_data

	# --- end of run (...) ---
