# R Overlay -- ebuild creation
# Copyright 2006-2012 Gentoo Foundation
# Distributed under the terms of the GNU General Public License v2

# temporary import until logging is implemented
from sys import stderr as logging

# temporary import until config and real constants are implemented
from roverlay import tmpconst as const

from roverlay.fileio import DescriptionReader

# misc TODO notes:
# * could use caching via decorators instead of wrappers (-> later)
# * instead of including the ebuild header in every ebuild 'export' data:
# ** link that header
# ** ebuild_export = [ <header_link>, str, [,str]* ]
#

class Ebuild:
	# could move this to const
	EBUILD_INDENT = "\t"

	# reading every ebuild header file (copyright, inherit <eclass>) once at most
	#  <ebuild header file> => [<content of this file>]
	#  shared among all ebuilds
	ebuild_headers = dict()

	@classmethod
	def __init__ ( self ):
		"""Initializes an empty Ebuild. This is an object that can be used to
		create text lines for an ebuild file."""

		self.name        = ''
		self.version     = ''
		self.origin      = ''
		self.pkg_file    = ''
		self.depend      = ''
		self.rdepend     = ''
		self.rsuggests   = ''
		self.description = ''

		# temporary var
		self.TODO = ''

		# this will be a list of str when exported data have been calculated
		self._ebuild_export = None

	@classmethod
	def get_ebuild ( self, force_update=False ):
		"""
		Wrapper function that returns ebuild 'export' data.
		This is a list of str that has no newline chars at the end of each str.

		arguments:
		* force_update -- force calculation of export data

		"""
		if force_update or (self._ebuild_export is None):
			self._ebuild_export = self._make_export()

		return self._ebuild_export

	@classmethod
	def suggest_filename ( self ):
		"""Suggests a file name for the ebuild.
		Calculated using ebuild data, but TODO
		"""
		# name-version
		return None

	@classmethod
	def write_ebuild ( self, file_to_write, force_update=False ):
		"""Writes this ebuild into a file

		arguments:
		* file_to_write -- path of the file to write (will be overwritten if existent)
		* force_update -- force calculation of ebuild data, don't use cached results

		**TODO notes : mkdir -p $(dirname)
		"""
		try:
			# try to get the ebuild lines before opening the file
			line  = None
			# append newline here or add in _make_export()
			lines = [ line + "\n" for line in self.get_ebuild ( force_update ) ]
			del line

			fh = open ( file_to_write, 'w' )
			fh.writelines ( lines )
			fh.close ()

			del lines, fh
			return True
		except IOError as err:
			raise

		# catch failure
		return False



	@staticmethod
	def _get_fileheader ( ebuild_header_file=None ):
		"""Reads and returns the content of an ebuild header file.
		This is a normal file that can be included in ebuilds.
		Every header file will only be read on first access, it's content will
		be stored in a dict that is shared among all Ebuild instances.

		arguments:
		ebuild_header_file -- path to the header file; defaults to none which
		                      means that nothing will be read and an empty list
		                      is returned
		"""
		if ebuild_header_file is None:
			# nothing to read
			return []

		elif (ebuild_header_file in ebuild_headers):
			# previously read
			return ebuild_headers [ebuild_header_file]

		else:
			# do read
			try:
				fh = open (ebuild_header_file, 'rU')
				lines = fh.readlines()
				fh.close()
				ebuild_headers [ebuild_header_file] = lines
				del lines, fh
				return ebuild_headers [ebuild_header_file]

			except IOError as err:
				raise

	@staticmethod
	def _make_var ( varname, value=None, indent_level=0 ):
		"""Returns a variable definitions that can be used in ebuilds, optionally
		with indention.

		arguments:
		* varname -- name of the variable (e.g. DEPEND)
		* value -- value of the variable; an empty var (DEPEND="") will be returned
		           if unset (the default)
		* indent_level -- indent var definition by indent_level levels
		"""

		if value:
			return indent_level * EBUILD_INDENT + varname + '"' + value + '"'
		else:
			# empty var
			return indent_level * EBUILD_INDENT + varname + '""'

	@classmethod
	def _make_export ( self, ebuild_header=None ):
		"""Creates ebuild data that can be written into stdout or a file

		arguments:
		ebuild_header_file -- path to the header file; defaults to none which
		                      means that nothing will be read and an empty list
		                      is returned
		"""

		# this method is todo

		errors = dict()

		ebuild_content = _get_fileheader ( ebuild_header )

		# repeated and leading empty lines will be removed later
		ebuild_content.append ( "" )

		if self.pkg_file:
			ebuild_content.append ( _make_var ( "PKG_FILE" , self.pkg_file ) )
		else:
			# absense of a pkg source file is an error
			errors ['PKG_FILE'] = "missing"

		if self.origin:
			ebuild_content.append ( _make_var ( "PKG_ORIGIN", self.origin ) )
		else:
			errors ['PKG_ORIGIN'] = "missing"

		ebuild_content.append ( "" )

		if self.description:
			ebuild_content.append ( _make_var ( "DESCRIPTION", self.TODO ) )
		else:
			ebuild_content.append ( _make_var ( "DESCRIPTION", "<none>" ) )
			#errors ['DESCRIPTION'] = "missing"

		# determine SRC_URI (origin + pkg_file)
		if self.pkg_file and self.origin and False:
			# SRC_URI ~= <> + origin + pkg_file
			ebuild_content.append ( _make_var ( "SRC_URI", "" ) )
		else:
			# either RESTRICT+=" fetch" or treat missing SRC_URI as critical
			errors ['SRC_URI'] = "missing"

		ebuild_content.append ( "" )

		#LICENSE (!!)

		rdepend = '${DEPEND:-} ' + self.rdepend

		# inherit IUSE from eclass
		iuse = '${IUSE:-}'

		if self.rsuggests:
			iuse    += ' R_suggests'
			rdepend += ' R_suggests ? ${R_SUGGESTS}'
			ebuild_content.append ( _make_var ( "R_SUGGESTS", self.rsuggests ) )

		ebuild_content.append ( _make_var ( "IUSE", iuse ) )
		ebuild_content.append ( "" )

		# DEPEND="${DEPEND:-} <pkg dependencies>" to inherit deps from eclass
		ebuild_content.append ( _make_var (
											"DEPEND", '${DEPEND:-} ' + self.depend ) )

		ebuild_content.append ( _make_var ( "RDEPEND", rdepend ) )

		# (!!) TODO
		if errors:
			raise Exception ( "^^^missing components for ebuild^^^" )
			#return None

		ebuild_export = []
		last_line_empty = False
		line = None

		# remove repeated newlines ('repoman sez: ...')
		for line in ebuild_content:
			line = line.rstrip()
			if line:
				last_line_empty = False
			elif not last_line_empty:
				last_line_empty = True
			else:
				continue

			ebuild_export.append ( line )


		del last_line_empty, line, ebuild_content
		return ebuild_export

class EbuildCreator:

		@classmethod
		def __init__ ( self,  description_data ):
			""""Initializes an EbuildCreator.
			[todo]
			"""
			self._description_data = description_data

			self._ebuild = None

		@classmethod
		def run ( self ):
			"""Tells this EbuildCreator to operate which produces an Ebuild object
			that can later be shown or written into a file.
			"""
			#todo
			self._ebuild = None

			if self._description_data is None:
				return False

			ebuild = Ebuild()
			dref = self._description_data

			ebuild.name = dref ['Package']
			ebuild.version = dref ['Version']

			ebuild.origin = "TODO"
			ebuild.pkg_file = "TODO"

			# depend rdepend rsuggest
			ebuild.depend  = "TODO"
			ebuild.rdepend = "TODO"
			ebuild.suggest = "TODO"

			if 'Description' in dref:
				ebuild.description = dref ['Description']
			elif 'Title' in dref:
				ebuild.description = dref ['Title']
			else:
				ebuild.description = "<none>"

			# <dep resolution here?>

			# todo
			return None


		@classmethod
		def show ( self ):
			"""Prints the ebuild to stdout/err or into log"""
			pass

		@classmethod
		def write ( self ):
			"""Writes the ebuild into a file"""
			pass

		@classmethod
		def ready ( self ):
			"""Returns true if an Ebuild has been produced, else false."""
			return not (self._ebuild is None)


class EbuildFactory:

		@classmethod
		def __init__ ( self ):
			"""Initializes an ebuild factory. This continously produces EbuildCreator
			for every get_ebuild_creator ( tarball ) call.
			"""
			self.desc_reader = DescriptionReader()

		@classmethod
		def get_ebuild_creator ( self, tarball ):
			"""Creates and returns an ebuild creator that will handle
			the data retrieved from <tarball>.

			arguments:
			* tarball -- tarball to read
			"""
			data = self.desc_reader.readfile ( tarball )
			if data:
				return EbuildCreator ( data )
			else:
				return None


