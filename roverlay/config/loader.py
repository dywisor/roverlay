# R overlay -- config module, config file loader
# Copyright 2006-2012 Gentoo Foundation
# Distributed under the terms of the GNU General Public License v2

import re
import shlex
import os.path

from roverlay.config          import fielddef
from roverlay.config.util     import get_config_path, unquote
from roverlay.config.entrymap import CONFIG_ENTRY_MAP

class ConfigLoader ( object ):

	# often used regexes
	DEFAULT_LIST_REGEX = re.compile ( '\s*[,;]{1}\s*' )
	WHITESPACE         = re.compile ( '\s+' )


	def __init__ ( self, config_tree, logger=None ):
		"""Initializes a ConfigLoader.

		arguments:
		* config_tree -- ConfigTree
		* logger      -- logger to use, defaults to config_tree's logger
		"""
		self.ctree = config_tree

		self.config_root = None

		self.logger   = self.ctree.logger if logger is None else logger
		self.fielddef = None

	# --- end of __init__ (...) ---

	def _setval ( self, path, value, allow_empty_value=False ):
		"""Sets a value in the config tree.

		arguments:
		* path              -- config path
		* value             -- config value
		* allow_empty_value --
		"""
		self.ctree._findpath (
			path,
			value=value,
			root=self.config_root,
			create=True,
			forceval=allow_empty_value,
			forcepath=False
		)
	# --- end of _setval (...) ---

	def _config_entry ( self, cref, option, value, config_root ):
		"""Adds a normal config entry to the assigned ConfigTree.

		arguments:
		* cref        -- reference to the config option's entry in the
		                  CONFIG_ENTRY_MAP
		* option      -- name of the config option
		* value       -- value read from a config file (will be verified here)
		* config_root -- ignored;
		"""
		# determine the config path
		path = None
		if 'path' in cref:
			path = cref ['path']
		else:
			path = option.split ( '_' )

		path = get_config_path ( path )

		# need a valid path
		if path:

			# verify and convert value if value_type is set
			if 'value_type' in cref:
				value = self._make_and_verify_value (
					cref ['value_type'], value
				)

			# need a valid value
			if value:

				self.logger.debug (
					"New config entry %s with path %s and value %s." %
						( option, path, value )
				)

				# add option/value to the config
				self._setval ( path, value )

				return True
			else:
				self.logger.error (
					"Option '%s' has an unusable value '%s'." %
						( real_option, value )
				)
				return False
		# ---
	# --- end of _config_enty (...) ---

	def _add_entry ( self, option, value=None, config_root=None ):
		"""Adds an option to the config.

		arguments:
		* option      -- name of the option as it appears in the config file
		* value       -- value to assign, defaults to None
		* config_root -- root of the config (a dict), defaults to None which is
		                 later understood as self._config
		"""

		real_option = option
		low_option = option.lower()

		# known option? option not empty and its lowercase repr in the entry map
		if option and low_option in CONFIG_ENTRY_MAP:

			original_cref = cref = CONFIG_ENTRY_MAP [low_option]
			cref_level = 0

			# check if cref is a link to another entry in CONFIG_ENTRY_MAP
			while isinstance ( cref, str ) and cref != '':
				if cref == original_cref and cref_level:
					self.logger.critical (
						"CONFIG_ENTRY_MAP is invalid! circular cref detected."
					)
					raise Exception ( "CONFIG_ENTRY_MAP is invalid!" )

				elif cref in CONFIG_ENTRY_MAP:
					option = low_option = cref
					cref = CONFIG_ENTRY_MAP [cref]
					cref_level += 1
				else:
					self.logger.critical (
						'CONFIG_ENTRY_MAP is invalid! '
						'last cref = %s, current cref = %s.' % ( option, cref )
					)
					raise Exception ( "CONFIG_ENTRY_MAP is invalid!" )

			# check if config entry is disabled
			if cref is None:
				# deftly ignored
				return True

			elif self._config_entry ( cref, option, value, config_root ):
				return True
			else:
				self.logger.error ( "Option '%s' is unusable..." % real_option )
				return False
		# ---

		self.logger.warning ( "Option '%s' is unknown." % real_option )
		return False

	# --- end of _add_entry (...) ---

	def load_config ( self, config_file ):
		"""Loads a config file and integrates its content into the config tree.
		Older config entries may be overwritten.

		arguments:
		config_file   -- path to the file that should be read
		"""

		# load file

		try:
			fh     = open ( config_file, 'r' )
			reader = shlex.shlex ( fh )
			reader.wordchars       += ' ,./$()[]:+-@*~'
			reader.whitespace_split = False


			nextline = lambda : ( reader.get_token() for n in range (3) )

			option, equal, value = nextline ()

			while equal == '=' or not ( option == value == reader.eof ):
				if equal == '=':
					self._add_entry ( option, value )
				else:

					self.logger.warning (
						"In '%s', cannot parse this line: '%s%s%s'." %
							( config_file, option, equal, value )
					)

				option, equal, value = nextline ()

			if fh:
				fh.close ()

		except IOError as ioerr:
			raise

	# --- end of load_config (...) ---

	def load_field_definition ( self, def_file, lenient=False ):
		"""Loads a field definition file.
		Please see the example file for format details.

		arguments:
		* def_file -- file (str) to read,
		               this can be a list of str if lenient is True
		* lenient  -- if True: do not fail if a file cannot be read;
		               defaults to False
		"""
		if self.fielddef is None:
			self.fielddef = fielddef.DescriptionFieldDefinition (
				self.logger
			)

		self.fielddef.load_file ( def_file, lenient=lenient )

		self.ctree._field_definition = self.fielddef.get()
	# --- end of load_field_definition (...) ---

	def _make_and_verify_value ( self, value_type, value ):
		"""Prepares the value of a config option so that it can be used
		in the config.

		arguments:
		* value_type -- type of the value,
							  look above for explanation concerning this
		* value      -- value to verify and transform
		"""

		def to_int ( val, fallback_value=-1 ):
			"""Tries to convert val to an int, returning a fallback value
			on any error.

			arguments:
			* val --
			* fallback_value --

			catches: ValueError in case of an unsuccesful int conversion
			raises: nothing
			"""
			try:
				ret = int ( val )
				return ret
			except ValueError as verr:
				return fallback_value
		# --- end of to_int (...) ---

		def yesno ( val ):
			"""Tries to canonize an yes or no value to its integer
			representation. Returns 1 if val means 'yes', 0 if 'no' and
			-1 otherwise.

			arguments:
			* val --
			"""
			if not val is None:
				to_check = str ( val ) . lower ()
				if to_check in [ 'y', 'yes', '1', 'true', 'enabled', 'on' ]:
					return 1
				elif to_check in [ 'n', 'no', '0', 'false', 'disabled', 'off' ]:
					return 0

			self.logger.warning ( to_check + " is not a valid yesno value." )
			return -1
		# --- end of yesno (...) ---

		def fs_path ( val ):
			"""val is a filesystem path - returns expanded path (~ -> HOME).

			arguments:
			* val --
			"""
			return os.path.expanduser ( val ) if val else None
		# --- end of fs_path (...) ---

		def fs_abs ( val ):
			"""val is a filesystem path - returns absolute + expanded path."""
			if val:
				return os.path.abspath ( os.path.expanduser ( val ) )
			else:
				return None


		def fs_file ( val ):
			""""val is a file - returns expanded path if it is
			an existent file or it does not exist.

			arguments:
			* val --
			"""
			retval = fs_abs ( val )
			if retval:
				if os.path.isfile ( retval ) or not os.path.exists ( retval ):
					return retval

			return None
		# --- end of fs_file (...) ---

		def fs_dir ( val ):
			"""val is a directory -- returns expanded path if it is
			an existent dir or it does not exist.

			arguments:
			* val --
			"""
			retval = fs_abs ( val )
			if retval:
				if os.path.isdir ( retval ) or not os.path.exists ( retval ):
					return retval

			return None
		# --- end of fs_dir (...) ---

		def repo ( val ):
			"""To be removed. (FIXME)"""
			if not val: return None

			name, sepa, remainder = val.partition ( ':' )

			if sepa != ':' or not name or not remainder: return None

			if remainder [0] == ':':
				# name::url
				return ( name, None, remainder [1:] )

			elif remainder [0] == '/':
				# name:dir:url
				_dir, sepa, url = remainder.partition ( ':' )
				if sepa != ':' or not url: return None
				if not _dir: _dir = None
				return ( name, _dir, url )
			else:
				return ( name, None, remainder )
		# --- end of repo (...) ---

		def _regex ( val ):
			"""val is a regex -- compile it if possible

			arguments:
			* val --
			"""
			return re.compile ( val ) if not val is None else None
		# --- end of _regex (...) ---

		# replace whitespace with a single ' '
		value = unquote ( ConfigLoader.WHITESPACE.sub ( ' ', value ) )

		# convert value_type into a list of value types
		if not value_type:
			return value
		elif isinstance ( value_type, list ):
			vtypes = value_type
		elif isinstance ( value_type, str ):
			vtypes = value_type.split ( ':' )
		else:
			self.logger.error ( "Unknown data type for value type." )
			return value

		# value_type -> function where function accepts one parameter
		funcmap = {
			'list'    : ConfigLoader.DEFAULT_LIST_REGEX.split,
			'slist'   : ConfigLoader.WHITESPACE.split,
			'yesno'   : yesno,
			'int'     : to_int,
			'fs_dir'  : fs_dir,
			'fs_path' : fs_path,
			'fs_file' : fs_file,
			'fs_abs'  : fs_abs,
			'regex'   : _regex,
			'str'     : str,
			'repo'    : repo,
		}

		# dofunc ( function f, <list or str> v) calls f(x) for every str in v
		dofunc = lambda f, v : [ f(x) for x in v ] \
			if isinstance ( v, list ) else f(v)

		retval = value.strip()

		for vtype in vtypes:
			if vtype in funcmap:
				retval = dofunc ( funcmap [vtype], retval )
			else:
				self.logger.warning ( "unknown value type '" + vtype + "'." )

		return retval
	# --- end of _make_and_verify_value (...) ---
