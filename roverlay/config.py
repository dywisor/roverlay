# R overlay -- config module
# Copyright 2006-2012 Gentoo Foundation
# Distributed under the terms of the GNU General Public License v2

import sys
import shlex
import copy

try:
	import configparser
except ImportError as running_python2:
	# configparser is named ConfigParser in python2
	import ConfigParser as configparser




from roverlay import descriptionfields
from roverlay import const




def access():
	"""Returns the ConfigTree."""
	return ConfigTree() if ConfigTree.instance is None else ConfigTree.instance
# --- end of access (...) ---


def get ( key, fallback_value=None ):
	"""Searches for key in the ConfigTree and returns its value if possible,
	else fallback_value.
	'key' is a config path [<section>[.<subsection>*]]<option name>.

	arguments:
	* key --
	* fallback_value --
	"""
	if fallback_value:
		return access().get ( key, fallback_value )
	else:
		return access().get ( key )
# --- end of get (...) ---


class InitialLogger:

	def __init__ ( self ):
		"""Initializes an InitialLogger.
		It implements the debug/info/warning/error/critical/exception methods
		known from the logging module and its output goes directly to sys.stderr.
		This can be used until the real logging has been configured.
		"""
		self.debug     = lambda x : sys.stderr.write ( "DBG  " + str ( x ) + "\n" )
		self.info      = lambda x : sys.stderr.write ( "INFO " + str ( x ) + "\n" )
		self.warning   = lambda x : sys.stderr.write ( "WARN " + str ( x ) + "\n" )
		self.error     = lambda x : sys.stderr.write ( "ERR  " + str ( x ) + "\n" )
		self.critical  = lambda x : sys.stderr.write ( "CRIT " + str ( x ) + "\n" )
		self.exception = lambda x : sys.stderr.write ( "EXC! " + str ( x ) + "\n" )

	# --- end of __init__ (...) ---

class ConfigTree:
	# static access to the first created ConfigTree
	instance = None

	def __init__ ( self, import_const=True ):
		"""Initializes an ConfigTree, which is a container for options/config values.
		values can be stored directly (such as the field_definitions) or in a
		tree-like { section -> subsection[s] -> option = value } structure.
		Config keys cannot contain dots because they're used as config path
		separator.

		arguments:
		* import_const -- whether to deepcopy constants into the config tree or
		                  not. Copying allows faster lookups.
		"""
		if ConfigTree.instance is None:
			ConfigTree.instance = self

		self.logger = InitialLogger()

		self.parser = dict()

		self._config = const.clone() if import_const else dict ()
		self._const_imported = import_const
		self._field_definitions = None

	# --- end of __init__ (...) ---


	def _findpath ( self, path, root=None, create=False ):
		if path is None:
			return root
		elif isinstance ( path, str ):
			path = path.split ( '.' ) if key else []

		config_position = self._config if root is None else root

		for k in path:
			if not k in config_position:
				if create:
					config_position [k] = dict ()

				else:
					return None

			config_position = config_position [k]

		return config_position

	# --- end of _findpath (...) ---


	def get ( self, key, fallback_value=None ):
		"""Searches for key in the ConfigTree and returns its value.
		Searches in const if ConfigTree does not contain the requested key and
		returns the fallback_value if key not found.

		arguments:
		* key --
		* fallback_value --
		"""
		if self._config:
			config_value = self._findpath ( key )

			if config_value:
				return config_value

		if self._const_imported:
			return fallback_value
		else:
			return const.lookup ( key, fallback_value )

	# --- end of get (...) ---

	def load_config ( self, config_file, start_section='' ):
		"""Loads a config file and integrates its content into the config tree.
		Older config entries may be overwritten.

		arguments:
		config_file   -- path to the file that should be read
		start_section -- relative root in the config tree as str or ref
		"""

		config_root = None
		if start_section:
			if isinstance ( start_section, str ):
				config_root = self._findpath ( start_section, None, True )
			elif isinstance ( start_section, dict ):
				config_root = start_section
			else
				raise Exception ("bad usage")

		# load file

		try:
			fh = open ( config_file, 'r' )
			reader = shlex.shlex ( fh )
			if fh:
				fh.close ()

			# <TODO>

		except IOError as ioerr:
			raise

	# --- end of load_config (...) ---

	def load_field_definition ( self, def_file, lenient=False ):
		"""Loads a field definition file. Please see the example file for format
		details.

		arguments:
		* def_file -- file (str) to read, this can be a list of str if lenient is True
		* lenient  -- if True: do not fail if a file cannot be read; defaults to False
		"""
		if not 'field_def' in self.parser:
			self.parser ['field_def'] = configparser.SafeConfigParser ( allow_no_value=True )

		try:
			self.logger.debug ( "Reading description field definition file " + def_file + "." )
			if lenient:
				self.parser ['field_def'] . read ( def_file )
			else:
				fh = open ( def_file, 'r' )
				self.parser ['field_def'] . readfp ( fh )
				if fh:
					fh.close()
		except IOError as err:
			self.logger.exception ( err )
			raise
		except configparser.MissingSectionHeaderError as mshe:
			self.logger.exception ( mshe )
			raise

	# --- end of load_field_definition (...) ---


	def get_field_definition ( self, force_update=False ):
		"""Gets the field definition stored in this ConfigTree.

		arguments:
		* force_update -- enforces recreation of the field definition data.
		"""
		if force_update or not self._field_definitions:
			self._field_definitions = self._make_field_definition ()

		return self._field_definitions

	# --- end of get_field_definition (...) ---


	def _make_field_definition ( self ):
		"""Creates and returns field definition data. Please see the example
		field definition config file for details.
		"""

		def get_list ( value_str ):
			if value_str is None:
				return []
			else:
				l = value_str.split ( ', ' )
				return [ e for e in l if e.strip() ]

		if not 'field_def' in self.parser:
			return None

		fdef = descriptionfields.DescriptionFields ()

		for field_name in self.parser ['field_def'].sections():
			field = descriptionfields.DescriptionField ( field_name )
			for option, value in self.parser ['field_def'].items ( field_name, 1 ):

				if option == 'alias' or option == 'alias_withcase':
					for alias in get_list ( value ):
						field.add_simple_alias ( alias, True )

				elif option == 'alias_nocase':
					for alias in get_list ( value ):
						field.add_simple_alias ( alias, False )

				elif option == 'default_value':
					field.set_default_value ( value )

				elif option == 'allowed_value':
					field.add_allowed_value ( value )

				elif option == 'allowed_values':
					for item in get_list ( value ):
						field.add_allowed_value ( item )

				elif option == 'flags':
					for flag in get_list ( value ):
						field.add_flag ( flag )
				else:
					# treat option as flag
					field.add_flag ( option )

			fdef.add ( field )

		return fdef

	# --- end of _make_field_definition (...) ---
