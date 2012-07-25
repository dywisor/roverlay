# R Overlay -- description reader
# Copyright 2006-2012 Gentoo Foundation
# Distributed under the terms of the GNU General Public License v2

import re
import tarfile
import os.path
import time

from roverlay          import config, util
from roverlay.rpackage import descriptionfields

LOG_IGNORED_FIELDS = True

def make_desc_packageinfo ( filepath ):
	"""Creates a minimal dict that can be used as package info in the
	DescriptionReader (for testing/debugging).

	arguments:
	* filepath --
	"""
	name, sep, ver = filepath.partition ( '_' )
	return dict (
		package_file  = filepath,
		package_name  = name,
		ebuild_verstr = ver,
		name          = name,
	)


class DescriptionReader ( object ):
	"""Description Reader"""

	WRITE_DESCFILES_DIR = config.get ( 'DESCRIPTION.descfiles_dir', None )

	def __init__ ( self,
		package_info, logger,
		read_now=False, write_desc=True
	):
		"""Initializes a DESCRIPTION file reader."""

		if not config.access().get_field_definition():
			raise Exception (
				"Field definition is missing, cannot initialize DescriptionReader."
			)

		self.field_definition = config.access().get_field_definition()
		self.fileinfo         = package_info
		self.logger           = logger.getChild ( 'desc_reader' )

		if write_desc and DescriptionReader.WRITE_DESCFILES_DIR is not None:
			self.write_desc_file  = os.path.join (
				DescriptionReader.WRITE_DESCFILES_DIR,
				'%s_%s.desc' % (
					self.fileinfo ['name'], self.fileinfo ['ebuild_verstr']
				)
			)

		if read_now:
			self.run()

	# --- end of __init__ (...) ---

	def get_desc ( self, run_if_unset=True ):
		if not hasattr ( self, 'desc_data' ):
			if run_if_unset:
				self.run()
			else:
				raise Exception ( "no desc data" )

		return self.desc_data
	# --- end of get_desc (...) ---

	def _make_read_data ( self, raw ):
		"""Create read data (value or list of values per field) for the given
		raw data (list of text lines per field).

		arguments:
		* raw --

		returns: read data
		"""
		# catch None
		if raw is None: return None

		# this dict will be returned as result later
		read = dict()

		flags = self.field_definition.get_fields_with_flag

		# insert default values
		default_values = self.field_definition.get_fields_with_default_value()

		for field_name in default_values.keys():
			if not field_name in raw:
				read [field_name] = default_values [field_name]


		# transfer fields from raw as string or list
		fields_join   = flags ( 'joinValues' )
		fields_isList = flags ( 'isList' )
		fields_wsList = flags ( 'isWhitespaceList' )

		list_split = re.compile (
			config.get_or_fail ( 'DESCRIPTION.list_split_regex' )
		).split
		slist_split = re.compile ( '\s+' ).split

		make_list  = lambda l : tuple ( filter ( None,  list_split ( l, 0 ) ) )
		make_slist = lambda l : tuple ( filter ( None, slist_split ( l, 0 ) ) )

		for field in raw.keys():

			# join (' ') > isList > wsList [... >= join ('', implicit)]

			if field in fields_join:
				read [field] = ' '.join ( filter ( None, raw [field] ) )

			else:
				value_line = ''.join ( filter ( None, raw [field] ) )

				if field in fields_isList:
					read [field] = make_list ( value_line )

				elif field in fields_wsList:
					read [field] = make_slist ( value_line )

				else:
					read [field] = value_line


		return read
	# --- end of _make_read_data (...) ---

	def _verify_read_data ( self, read ):
		"""Verifies read data.
		Checks that all mandatory fields are set and all fields have suitable
		values.

		Returns True (^= valid data) or False (^= cannot use package)
		"""
		fref = self.field_definition

		# ensure that all mandatory fields are set
		missing_fields = set ()

		for field in fref.get_fields_with_flag ( 'mandatory' ):

			if field in read:
				if read [field] is None or len ( read [field] ) < 1:
					missing_fields.add ( field )
				#else: ok
			else:
				missing_fields.add ( field )


		# check for fields that allow only certain values
		unsuitable_fields = set()

		restricted_fields = fref.get_fields_with_allowed_values()

		for field in restricted_fields:
			if field in read:
				if not fref.get ( field ).value_allowed ( read [field] ):
					unsuitable_fields.add ( field )

		# summarize results
		valid = not len ( missing_fields ) and not len ( unsuitable_fields )
		if not valid:
			self.logger.info ( "Cannot use R package" ) # name?
			if len ( missing_fields ):
				self.logger.debug (
					"The following mandatory description fields are missing: %s."
						% missing_fields
				)
			if len ( unsuitable_fields ):
				self.logger.debug (
					"The following fields have unsuitable values: %s."
						% unsuitable_fields
				)

		return valid

	# --- end of _verify_read_data (...) ---

	def _get_desc_from_file ( self, filepath, pkg_name='.' ):
		"""Reads a file returns the description data.

		arguments:
		* filepath -- file to read (str; path to tarball or file)
		* pkg_name -- name of the package, in tarballs the description file
						  is located in <pkg_name>/ and thus this argument
						  is required. Defaults to '.', set to None to disable.

		All exceptions are passed to the caller (TarError, IOErr, <custom>).
		<filepath> can either be a tarball in which case the real DESCRIPTION
		file is read (<pkg_name>/DESCRIPTION) or a normal file.
		"""

		self.logger.debug ( "Starting to read file '%s' ...\n" % filepath )

		if not ( isinstance ( filepath, str ) and filepath ):
			raise Exception ( "bad usage" )

		# read describes how to import the lines from a file (e.g. rstrip())
		#  fh, th are file/tar handles
		read = th = fh = None

		if tarfile.is_tarfile ( filepath ):
			# filepath is a tarball, open tar handle + file handle
			th = tarfile.open ( filepath, mode='r' )
			if pkg_name:
				fh = th.extractfile (
					pkg_name + os.path.sep + config.get ( 'DESCRIPTION.file_name' )
				)
			else:
				fh = th.extractfile ( config.get ( 'DESCRIPTION.file_name' ) )

		else:
			# open file handle only (!! .Z compressed tar files, FIXME)
			fh = open ( filepath, 'r' )


		# decode lines of they're only bytes, using isinstance ( <>, str )
		# 'cause isinstance ( <str>, bytes ) returns True
		read_lines = tuple (
			( line if isinstance ( line, str ) else line.decode() ).rstrip()
				for line in fh.readlines()
		)

		fh.close()
		if not th is None: th.close()
		del fh, th

		if read_lines and hasattr ( self, 'write_desc_file' ):
			try:
				util.dodir ( DescriptionReader.WRITE_DESCFILES_DIR )
				fh = open ( self.write_desc_file, 'w' )
				fh.write (
					'=== This is debug output (%s) ===\n'
						% time.strftime ( '%F %H:%M:%S' )
				)
				fh.write ( '\n'.join ( read_lines ) )
				fh.write ( '\n' )
			finally:
				if 'fh' in locals() and fh: fh.close()


		return read_lines

	# --- end of _get_desc_from_file (...) ---

	def _get_raw_data ( self ):
		try:
			desc_lines = self._get_desc_from_file (
				self.fileinfo ['package_file'],
				self.fileinfo ['package_name']
			)

		except Exception as err:
			#self.logger.exception ( err )
			# error message should suffice
			self.logger.warning ( err )
			return None

		raw = dict()

		field_context = None

		comment_chars = config.get ( 'DESCRIPTION.comment_chars', '#' )

		non_ascii_warned = False

		for line in desc_lines:
			field_context_ref = None

			# using s(tripped)line whenever whitespace doesn't matter
			sline = line.lstrip()

			if not sline or line [0] in comment_chars:
				# empty line or comment
				pass

			elif line [0] != sline [0]:
				# line starts with whitespace

				if field_context:
					# context is set => append values

					raw [field_context].append ( sline )

				else:
					# no valid context => ignore line
					pass

			else:
				# line has to introduce a new field context, forget last one
				field_context = None

				line_components = sline.partition (
					config.get ( 'DESCRIPTION.field_separator', ':' )
				)

				if line_components [1]:
					# line contains a field separator => new context, set it
					field_context_ref = self.field_definition.get (
						line_components [0]
					)

					if field_context_ref is None:
						# field not defined, skip
						self.logger.info (
							"Skipped a description field: '%s'.", line_components [0]
						)
					elif field_context_ref.has_flag ( 'ignore' ):
						# field ignored
						if LOG_IGNORED_FIELDS:
							self.logger.debug (
								"Ignored field '%s'.", field_context_ref.get_name()
							)

					else:
						field_context = field_context_ref.get_name()

						if not field_context:
							raise Exception (
								'Field name is not valid! This should\'ve '
								'already been catched in DescriptionField...'
							)

						if field_context in raw:
							# some packages have multiple Title fields
							# warn about that 'cause it could lead to confusing
							# ebuild/metadata output
							self.logger.warning (
								"field {} redefined!".format ( field_context )
							)

							raw [field_context].append ( sline )

						else:
							# add values to read_data, no need to check
							#  line_components [2] 'cause [1] was a true str
							# create a new empty list for this field_context
							raw[field_context] = [ line_components [2].lstrip() ]

				else:
					# reaching this branch means that
					#  (a) line has no leading whitespace
					#  (b) line has no separator (:)
					# this should not occur in description files (bad syntax,
					# unknown compression (.Z!))

					# !!! FIXME: handle .Z files properly or at least
					# deny to read them
					# remove non ascii-chars (could confuse the terminal)
					ascii_str = util.ascii_filter ( line_components [0] )
					if len ( ascii_str ) == len ( line_components [0] ):
						self.logger.warning (
							"Unexpected line in description file: {!r}.".format (
								line_components [0]
						) )
					elif not non_ascii_warned:
						# probably compressed text
						self.logger.warning (
							'Unexpected non-ascii line in description '
							'file (compressed text?)!'
						)
						non_ascii_warned = True

		# -- end for --

		return raw
	# --- end of _get_raw_data (...) ---

	def run ( self ):
		"""Reads a DESCRIPTION file and returns the read data if successful,
		else None.

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

		raw_data  = self._get_raw_data()
		read_data = self._make_read_data ( raw_data )

		self.desc_data = None

		if read_data is None:
			self.logger.warning (
				"Failed to read file {f!r}.".format (
					f=self.fileinfo ['package_file']
			) )

		elif self._verify_read_data ( read_data ):
			self.logger.debug (
				"Successfully read file {f} with data = {d}.".format (
					f=self.fileinfo ['package_file'], d=read_data
			) )
			self.desc_data = read_data

		# else have log entries from _verify()

	# --- end of run (...) ---
