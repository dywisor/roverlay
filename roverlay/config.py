# R overlay -- config module
# Copyright 2006-2012 Gentoo Foundation
# Distributed under the terms of the GNU General Public License v2

import os.path
import re
import sys
import shlex

try:
	import configparser
except ImportError as running_python2:
	# configparser is named ConfigParser in python2
	import ConfigParser as configparser


from roverlay          import const
from roverlay.rpackage import descriptionfields


CONFIG_INJECTION_IS_BAD = True

def access():
	"""Returns the ConfigTree."""
	return ConfigTree() if ConfigTree.instance is None else ConfigTree.instance
# --- end of access (...) ---


def get ( key, fallback_value=None, fail_if_unset=False ):
	"""Searches for key in the ConfigTree and returns its value if possible,
	else fallback_value.
	'key' is a config path [<section>[.<subsection>*]]<option name>.

	arguments:
	* key --
	* fallback_value --
	"""
	if not fallback_value is None:
		return access().get (
			key, fallback_value=fallback_value, fail_if_unset=fail_if_unset
		)
	else:
		return access().get (
			key, fallback_value=None, fail_if_unset=fail_if_unset
		)
# --- end of get (...) ---

def get_or_fail ( key ):
	return access().get ( key, fail_if_unset=True )
# --- end of get_or_fail (...) ---

class InitialLogger:

	def __init__ ( self ):
		"""Initializes an InitialLogger.
		It implements the debug/info/warning/error/critical/exception methods
		known from the logging module and its output goes directly to sys.stderr.
		This can be used until the real logging has been configured.
		"""
		# @return None
		self.debug     = lambda x : sys.stdout.write ( "DBG  %s\n" % x )
		self.info      = lambda x : sys.stdout.write ( "INFO %s\n" % x )
		self.warning   = lambda x : sys.stderr.write ( "WARN %s\n" % x )
		self.error     = lambda x : sys.stderr.write ( "ERR  %s\n" % x )
		self.critical  = lambda x : sys.stderr.write ( "CRIT %s\n" % x )
		self.exception = lambda x : sys.stderr.write ( "EXC! %s\n" % x )

	# --- end of __init__ (...) ---

class ConfigTree ( object ):
	# static access to the first created ConfigTree
	instance = None

	# the map of config entries (keep keys in lowercase)
	#  format is config_entry = None|''|str|dict(...), where
	#   None   means that config_entry is known but ignored,
	#   str    means that config_entry is an alias for another config entry,
	#   ''     means that config_entry uses defaults,
	#   dict() means that config_entry has options / diverts from defaults.
	#
	# known dict keys are:
	# * path = str | list of str -- path of this entry in the config tree
	#
	# * value_type, you can specify:
	# ** slist   -- value is a whitespace-separated list
	# ** list    -- value is a list, see DEFAULT_LIST_REGEX below
	# ** int     -- integer
	# ** yesno   -- value must evaluate to 'yes' or 'no' (on,off,y,n,1,0...)
	# ** fs_path -- ~ will be expanded
	# ** fs_dir  -- fs_path and value must be a dir if it exists
	# ** fs_file -- fs_path and value must be a file if it exists
	# TODO** fs_prog -- fs_file (and fs_path) and value must be executable (TODO)
	# ** regex   -- value is a regex and will be compiled (re.compile(..))
	#
	#   multiple types are generally not supported ('this is an int or a str'),
	#   but subtypes are (list of yesno), which can be specified by either
	#   using a list of types ['list', 'yesno'] or by separating the types
	#   with a colon list:yesno, which is parsed in a left-to-right order.
	#   Nested subtypes such as list:slist:int:fs_file:list may lead to errors.
	#
	CONFIG_ENTRY_MAP = dict (
		log_level = '',
		log_console = dict (
			value_type = 'yesno',
		),
		log_file = dict (
			# setting path to LOG.FILE.main to avoid collision with LOG.FILE.*
			path       = [ 'LOG', 'FILE', 'main' ],
			value_type = 'fs_file',
		),
		log_file_resolved = dict (
			value_type = 'fs_file',
		),
		log_file_unresolvable = dict (
			value_type = 'fs_file',
		),
		ebuild_header = dict (
			value_type = 'fs_file',
		),
		overlay_dir   = dict (
			value_type = 'fs_dir',
		),
		distfiles_dir = dict (
			value_type = 'fs_dir',
		),
		ebuild_prog = dict (
			path       = [ 'TOOLS', 'ebuild_prog' ],
			value_type = 'fs_path',
		),

	)

	# often used regexes
	DEFAULT_LIST_REGEX = re.compile ( '\s*[,;]{1}\s*' )
	WHITESPACE         = re.compile ( '\s+' )


	def __init__ ( self, import_const=True ):
		"""Initializes an ConfigTree, which is a container for options/values.
		Values can be stored directly (such as the field_definitions) or
		in a tree-like { section -> subsection[s] -> option = value } structure.
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


	def _findpath ( self, path, root=None, create=False, value=None ):
		"""All-in-one method that searches for a config path.
		It is able to create the path if non-existent and to assign a
		value to it.

		arguments:
		* path   -- config path as path list ([a,b,c]) or as path str (a.b.c)
		* root   -- config root (dict expected).
		             Uses self._config if None (the default)
		* create -- create path if nonexistent
		* value  -- assign value to the last path element
		             an empty dict will be created if this is None and
		             create is True
		"""
		if path is None:
			return root
		elif isinstance ( path, str ):
			path = path.split ( '.' ) if path else []

		config_position = self._config if root is None else root

		if config_position is None: return None

		for k in path:
			if len (k) == 0:
				continue
			if k == path [-1] and not value is None:
				# overwrite entry
				config_position [k] = value
			elif not k in config_position:
				if create:
						config_position [k] = dict()
				else:
					return None

			config_position = config_position [k]

		return config_position

	# --- end of _findpath (...) ---

	def inject ( self, key, value, suppress_log=False ):
		"""This method offer direct write access to the ConfigTree. No checks
		will be performed, so make sure you know what you're doing.

		arguments:
		* key -- config path of the entry to-be-created/overwritten
		          the whole path will be created, this operation does not fail
		          if a path component is missing ('<root>.<new>.<entry> creates
		          root, new and entry if required)
		* value -- value to be assigned

		returns: None (implicit)
		"""
		if not suppress_log:
			msg = 'config injection: value %s will '\
				'be assigned to config key %s ...' % ( value, key )

			if CONFIG_INJECTION_IS_BAD:
				self.logger.warning ( msg )
			else:
				self.logger.debug ( msg )

		self._findpath ( key, create=True, value=value )
	# --- end of inject (...) ---

	def get ( self, key, fallback_value=None, fail_if_unset=False ):
		"""Searches for key in the ConfigTree and returns its value.
		Searches in const if ConfigTree does not contain the requested key and
		returns the fallback_value if key not found.

		arguments:
		* key --
		* fallback_value --
		* fail_if_unset -- fail if key is neither in config nor const
		"""

		config_value = self._findpath ( key )

		if config_value is None:
			fallback = None if fail_if_unset else fallback_value
			if not self._const_imported:
				config_value = const.lookup ( key, fallback )
			else:
				config_value = fallback

			if config_value is None and fail_if_unset:
				raise Exception ( "config key '%s' not found but required." % key )

		return config_value

	# --- end of get (...) ---

	def _add_entry ( self, option, value=None, config_root=None ):
		"""Adds an option to the config.

		arguments:
		* option      -- name of the option as it appears in the config file
		* value       -- value to assign, defaults to None
		* config_root -- root of the config (a dict), defaults to None which is
		                 later understood as self._config
		"""

		def make_and_verify_value ( value_type, value, entryconfig_ref ):
			"""Prepares the value of a config option so that it can be used
			in the ConfigTree.

			arguments:
			* value_type      -- type of the value,
			                      look above for explanation concerning this
			* value           -- value to verify and transform
			* entryconfig_ref -- reference to the config entry config
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

			def fs_file ( val ):
				""""val is a file - returns expanded path if it is
				an existent file or it does not exist.

				arguments:
				* val --
				"""
				if val:
					retval = os.path.expanduser ( val )
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
				if val:
					retval = os.path.expanduser ( val )
					if os.path.isdir ( retval ) or not os.path.exists ( retval ):
						return retval

				return None
			# --- end of fs_dir (...) ---

			def _regex ( val ):
				"""val is a regex -- compile it if possible

				arguments:
				* val --
				"""
				return re.compile ( val ) if not val is None else None
			# --- end of _regex (...) ---

			# replace whitespace with a single ' '
			value = ConfigTree.WHITESPACE.sub ( ' ', value )

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
				'list'    : ConfigTree.DEFAULT_LIST_REGEX.split,
				'slist'   : ConfigTree.WHITESPACE.split,
				'yesno'   : yesno,
				'int'     : to_int,
				'fs_path' : fs_path,
				'fs_file' : fs_file,
				'regex'   : _regex,
			}

			# dofunc ( function f, <list or str> v) calls f(x) for every str in v
			dofunc = lambda f, v : [ f(x) for x in v ] \
				if isinstance ( v, list ) else f(v)

			retval = value

			for vtype in vtypes:
				if vtype in funcmap:
					retval = dofunc ( funcmap [vtype], retval )
				else:
					self.logger.warning ( "unknown value type '" + vtype + "'." )

			return retval
		# --- end of make_and_verify_value (...) ---


		real_option = option
		low_option = option.lower()

		# known option?
		if option and low_option in ConfigTree.CONFIG_ENTRY_MAP:

			original_cref = cref = ConfigTree.CONFIG_ENTRY_MAP [low_option]
			cref_level = 0

			# check if cref is a link to another entry in CONFIG_ENTRY_MAP
			while isinstance ( cref, str ) and cref != '':
				if cref == original_cref and cref_level:
					self.logger.critical (
						"CONFIG_ENTRY_MAP is invalid! circular cref detected."
					)
					raise Exception ( "CONFIG_ENTRY_MAP is invalid!" )

				elif cref in ConfigTree.CONFIG_ENTRY_MAP:
					option = low_option = cref
					cref = ConfigTree.CONFIG_ENTRY_MAP [cref]
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


			# determine the config path
			path = None
			if 'path' in cref:
				path = cref ['path']
			else:
				path = low_option.split ( '_' )
				for n in range ( len ( path ) - 1 ):
					path [n] = path [n].upper()

			# need a valid path
			if path:

				# verify and convert value if value_type is set
				if 'value_type' in cref:
					value = make_and_verify_value (
						cref ['value_type'], value, cref
					)

				# need a valid value
				if value:

					self.logger.debug (
						"New config entry %s with path %s and value %s." %
							( option, path, value )
					)

					# add option/value to the config
					self._findpath ( path, config_root, True, value )

					return True
				else:
					self.logger.error (
						"Option '%s' has an unusable value '%s'." %
							( real_option, value )
					)
					return False
			# ---

			self.logger.error ( "Option '%s' is unusable..." % real_option )
			return False
		# ---

		self.logger.warning ( "Option '%s' is unknown." % real_option )
		return False

	# --- end of _add_entry (...) ---

	def load_config ( self, config_file, start_section='' ):
		"""Loads a config file and integrates its content into the config tree.
		Older config entries may be overwritten.

		arguments:
		config_file   -- path to the file that should be read
		start_section -- relative root in the config tree as str
		"""

		config_root = None
		if start_section:
			if isinstance ( start_section, str ):
				config_root = self._findpath ( start_section, None, True )
			else:
				raise Exception ("bad usage")

		# load file

		try:
			fh     = open ( config_file, 'r' )
			reader = shlex.shlex ( fh )
			reader.wordchars       += ' ./$()[]:+-@*~'
			reader.whitespace_split = False



			nextline = lambda : ( reader.get_token() for n in range (3) )

			option, equal, value = nextline ()

			while equal == '=' or not ( option == value == reader.eof ):
				if equal == '=':
					self._add_entry ( option, value, config_root )
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
		if not 'field_def' in self.parser:
			self.parser ['field_def'] = \
				configparser.SafeConfigParser ( allow_no_value=True )

		try:
			self.logger.debug (
				"Reading description field definition file %s." % def_file
			)
			if lenient:
				self.parser ['field_def'] . read ( def_file )
			else:
				fh = open ( def_file, 'r' )
				self.parser ['field_def'] . readfp ( fh )

				if fh: fh.close()
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

		if not 'field_def' in self.parser: return None

		fdef = descriptionfields.DescriptionFields ()

		for field_name in self.parser ['field_def'].sections():
			field = descriptionfields.DescriptionField ( field_name )
			for option, value in self.parser ['field_def'].items( field_name, 1 ):

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
