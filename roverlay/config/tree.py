# R overlay -- config module
# Copyright 2006-2012 Gentoo Foundation
# Distributed under the terms of the GNU General Public License v2

import sys

from roverlay.config        import const
from roverlay.config.loader import ConfigLoader
from roverlay.config.util   import get_config_path

CONFIG_INJECTION_IS_BAD = True

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

		self._config = const.clone() if import_const else dict ()
		self._const_imported    = import_const
		self._field_definition  = None

	# --- end of __init__ (...) ---

	def get_loader ( self ):
		return ConfigLoader ( self )
	# --- end of get_loader (...) ---

	def _findpath ( self, path,
		root=None, create=False, value=None, forcepath=False, forceval=False
	):
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
		* forcepath -- if set and True: do not 'normalize' path if path is a list
		* forceval  -- if set and True: accept None as value
		"""
		if path is None:
			return root
		elif isinstance ( path, ( list, tuple ) ) and forcepath:
			pass
		else:
			path = get_config_path ( path )


		config_position = self._config if root is None else root

		if config_position is None: return None

		last = len ( path ) - 1

		for index, k in enumerate ( path ):
			if len (k) == 0:
				continue

			if index == last and ( forceval or not value is None ):
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

	def inject ( self, key, value, suppress_log=False, **kw_extra ):
		"""This method offer direct write access to the ConfigTree. No checks
		will be performed, so make sure you know what you're doing.

		arguments:
		* key -- config path of the entry to-be-created/overwritten
		          the whole path will be created, this operation does not fail
		          if a path component is missing ('<root>.<new>.<entry> creates
		          root, new and entry if required)
		* value -- value to be assigned
		* **kw_extra -- extra keywords for _findpath, e.g. forceval=True

		returns: None (implicit)
		"""
		if not suppress_log:
			msg = 'config injection: value %s will '\
				'be assigned to config key %s ...' % ( value, key )

			if CONFIG_INJECTION_IS_BAD:
				self.logger.warning ( msg )
			else:
				self.logger.debug ( msg )

		self._findpath ( key, create=True, value=value, **kw_extra )
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

	def get_field_definition ( self, force_update=False ):
		"""Gets the field definition stored in this ConfigTree.

		arguments:
		* force_update -- enforces recreation of the field definition data.
		"""
		return self._field_definition
	# --- end of get_field_definition (...) ---

	def _tree_to_str ( self, root, name, level=0 ):
		"""Returns string representation of a config tree rooted at root.
		Uses recursion (DFS).

		arguments:
		* root  -- config 'root', is a value (config 'leaf') or a dict ('tree')
		* name  --
		* level --

		returns: string representation of the given root
		"""

		indent = level * ' '
		var_indent =  indent + '* '
		if root is None:
			return "%s%s is unset\n" % ( var_indent, name )
		elif len ( root ) == 0:
			return "%s%s is empty\n" % ( var_indent, name )
		elif isinstance ( root, dict ):
			extra = ''.join ( [
				self._tree_to_str ( n, r, level+1 ) for r, n in root.items()
			] )
			return "%s%s {\n%s%s}\n" % ( indent, name, extra, indent )
		else:
			return "%s%s = '%s'\n" % ( var_indent, name, root )
	# --- end of _tree_to_str (...) ---

	def visualize ( self, into=None ):
		"""Visualizes the ConfigTree,
		either into a file-like object or as return value.

		arguments:
		* into -- if not None: write into file

		returns: string if into is None, else None (implicit)
		"""
		_vis = self._tree_to_str ( self._config, 'ConfigTree', level=0 )
		if into is None:
			return _vis
		else:
			into.write ( _vis )
	# --- end of visualize (...) ---
