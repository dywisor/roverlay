# R overlay -- simple dependency rules, console
# -*- coding: utf-8 -*-
# Copyright (C) 2012 André Erdmann <dywi@mailerd.de>
# Distributed under the terms of the GNU General Public License;
# either version 2 of the License, or (at your option) any later version.

"""dependency resolution console

This module provides console access to a (self-managed) dependency resolver
and is meant for testing.

Furthermore, its commands can be given through a stdin-pipe:
echo -e 'lc\n? <dep str>\n? <dep str2>' | roverlay depres
"""
__all__ = [ 'DepResConsole', ]

import re
import os
import sys
import shlex
import logging

from roverlay                                import config, strutil
from roverlay.errorqueue                     import ErrorQueue
from roverlay.depres                         import deptype
from roverlay.depres.depresolver             import DependencyResolver
from roverlay.depres.channels                import EbuildJobChannel
from roverlay.depres.simpledeprule           import rules
from roverlay.depres.simpledeprule.pool      import SimpleDependencyRulePool
from roverlay.depres.simpledeprule.rulemaker import SimpleRuleMaker

class PackageDirRuleMaker ( object ):
	"""Scans a distdir and creates selfdep rules for it.
	Part of the console module 'cause only used here. The overlay package
	has its own implementation that automatically uses all added packages
	for resolving dependencies.
	"""
	def __init__ ( self, fuzzy=True ):
		"""Initializes a PackageDirRuleMaker that will create fuzzy rules if
		'fuzzy' is True, else normal ones.
		"""
		self.fuzzy = fuzzy
		self.package_regex = re.compile (
			"^(?P<name>[^_]+)_.+{}$".format (
				config.get_or_fail ( 'R_PACKAGE.suffix_regex' )
			)
		)
	# --- end of __init__ (...) ---

	def _scan ( self, distdir ):
		"""
		Traverses through a distdir and yields the names of found R packages.

		arguments:
		* distdir --
		"""
		for dirpath, dirnames, filenames in os.walk ( distdir ):
			for filename in filenames:
				m = self.package_regex.match ( filename )
				if m is not None:
					yield m.group ( 'name' )
	# --- end of _scan (...) ---

	def make_rules ( self, distdir ):
		"""Consecutively creates and yields dependency rules for R packages
		found in the given distdir.

		arguments:
		* distdir --
		"""
		cat = config.get_or_fail ( 'OVERLAY.category' ) + '/'
		if self.fuzzy:
			for dep in self._scan ( distdir ):
				yield rules.SimpleFuzzyDependencyRule (
					resolving_package = strutil.fix_ebuild_name ( cat + dep ),
					dep_str = dep,
					is_selfdep=True
				)
		else:
			for dep in self._scan ( distdir ):
				yield rules.SimpleDependencyRule (
					resolving_package = strutil.fix_ebuild_name ( cat + dep ),
					dep_str = dep,
					is_selfdep=True
				)
	# --- end of make_rules (...) ---


class DepResConsole ( object ):
	# !! The console is really inefficient in terms of using cached data,
	# saving functions calls, ...
	# It's assumed that the user is still slower ;)

	shlex      = shlex.shlex()
	whitespace = re.compile ( "\s+" )

	# the command usage dict
	CMD_USAGE = {
		'add_pool' : """
			Creates a new pool on top of any existing ones.

			Arguments: None (ignored)

			Usage:
			* add_pool|<<
		""",
		'addrule' : """
			Creates a new dependency rule and adds it to the current rule pool.
			The console supports single-line rules only at this time.

			Arguments: a list of quoted rule strings if shlex mode is active,
			else one rule string

			Usage:
			* +|addrule <rule>
			* +|addrule "<rule>" ["<rule>"]*

		""",
		'help' : """
			Prints a general help message, a list of all help topics if --list\\
			is given, or a specific help message for the given command.

			Arguments: None, '--list', or a command

			Usage:
			* help
			* help --list
			* help <command>
		""",
		'load' : """
			Loads a rule file or directory into a new dependency rule pool.

			Arguments: a file

			Usage:
			* load|li|l <file|dir>
		""",
		'load_conf' : """
			Loads the rule files listed in the config file.

			Arguments: None (ignored)

			Usage:
			* load_conf|lc
		""",
		'mkhelp' : """
			Verifies that all usable commands have a help message.

			Arguments: None (ignored)

			Usage:
			* mkhelp
		""",
		'print': """
			Prints the content of the current pool or all pools.

			Arguments: 'all' (=> print all pools)

			Usage:
			* print
			* print all
		""",
		'resolve': """
			Resolves one or more dependency strings.

			Arguments: a list of quoted dependency strings if shlex mode is\\
			active, else one dependency string.

			Usage:
			* resolve|r|? <dependency string>
			* resolve|r|? "<dependency string>" ["<dependency string>"]*
		""",
		'scandir' : """
			Scans a directory for R packages and creates dependency rules\\
			for them.

			Arguments: a directory

			Usage:
			* scandir|sd <directory>
		""",
		'set' : """
			Set or unset modes. Prints all modes and their state when called\\
			with no args.
			Currently, the only available mode is 'shlex' which enables/disables\\
			shell-like argument parsing.\\
			Shlex mode allows to specify more than one arg when running certain
			commands, but requires args to be enclosed with quotes.

			Arguments: None or a mode

			Usage:
			* set
			* unset
			* set <mode>
			* unset <mode>
		""",
		'unwind' : """
			Removes the top-most (latest) dependency rule pool and all of its\\
			rules.

			Arguments: None (ignored)

			Usage:
			* unwind|>>
		""",
		'write' : """
			Writes the rules of the top-most (latest) dependency rule pool to\\
			a file that later be loaded.

			Arguments: file to write

			Usage:
			* write|w <file>
		""",
		'cd' : """
			Changes the working directory to the given one. Also creates it\\
			if necessary.

			Arguments: a directory

			Usage:
			* cd <directory>
		""",
	}

	CMD_USAGE_REDIRECT = {
		'r'     : 'resolve',
		'?'     : 'resolve',
		'sd'    : 'scandir',
		'+'     : 'addrule',
		'li'    : 'load',
		'l'     : 'load',
		'lc'    : 'load_conf',
		'w'     : 'write',
		'p'     : 'print',
		'>>'    : 'unwind',
		'<<'    : 'add_pool',
		'unset' : 'set',
		'h'     : 'help',
	}

	def _create_command_table ( self ):
		# the command table
		#  each command string is mapped to a function/method
		self.cmd_table = {
			'resolve'   : self.cmd_resolve,
			'scandir'   : self.cmd_rule_scandir,
			'addrule'   : self.cmd_rule_add,
			'load'      : self.cmd_rule_load,
			'load_conf' : self.cmd_rule_load_from_config,
			'write'     : self.cmd_pool_write,
			'print'     : self.cmd_pool_print,
			'unwind'    : self.cmd_pool_unwind,
			'add_pool'  : self.cmd_pool_add,
			'cd'        : self.cmd_cd,
			'set'       : self.cmd_set,
			'unset'     : self.cmd_unset,
			'help'      : self.cmd_help,
			'mkhelp'    : self.cmd_mkhelp,
		}

		for alias, real in self.__class__.CMD_USAGE_REDIRECT.items():
			self.cmd_table [alias] = self.cmd_table [real]
	# --- end of _create_command_table (...) ---

	def _get_usage ( self, func_name ):
		"""Returns the usage string for the given function (by name).

		arguments:
		* func_name
		"""
		if func_name in self.__class__.CMD_USAGE_REDIRECT:
			fname = self.__class__.CMD_USAGE_REDIRECT [func_name]
		else:
			fname = func_name

		if fname not in self._usage_dict:
			lines = list()
			for line in self.__class__.CMD_USAGE [fname].split ( '\n' ):
				line = line.strip()
				if len ( line ) or len ( lines ):
					lines.append ( line )

			if len ( lines ) and not len ( lines [-1] ):
				lines.pop()

			self._usage_dict [fname] = '\n'.join ( lines ).replace ( '\\\n', ' ' )

		return self._usage_dict [fname]
	# --- end of _get_usage (...) ---

	def _print_usage ( self, func_name ):
		"""Prints a usage message for the given function (by name)."""
		print (
			"command {!r}, usage:\n".format ( func_name ) + \
			self._get_usage ( func_name )
		)
	# --- end of _print_usage (...) ---

	def usage ( self ):
		"""Prints a usage message for the command currently running and
		returns False."""
		self._print_usage ( self._current_command )
		return False
	# --- end of usage (...) ---

	def __init__ ( self ):
		"""Initializes a dependency resolution console."""
		self.err_queue = ErrorQueue()

		# set up the resolver
		self.resolver = DependencyResolver ( err_queue=self.err_queue )
		# log everything
		self.resolver.set_logmask ( -1 )
		# disable passing events to listeners
		self.resolver.set_listenermask ( 0 )

		# dependency rule pools (a set of rules) are organized in a FIFO
		# structure that allows to create and delete new pools at runtime
		self.poolstack = self.resolver.static_rule_pools
		self.pool_id   = 0

		# this rule maker is used to convert input (strings) into dependency
		# rules
		self._rule_maker     = SimpleRuleMaker()

		# this rule maker is used to create rules for R packages found in
		# directories
		self._dir_rule_maker = PackageDirRuleMaker()

		# used for relative file paths (rule file writing,...)
		self._cwd = None

		# shlex mode:
		#  if True: split command args using shell syntax
		#  else   : treat command args as one arg

		# e.g. 'resolve zoo >= 5',
		# => command is 'resolve'
		# => args:
		#      shlex: [ 'zoo', '>=' , '5', ]
		#   no-shlex: [ 'zoo >= 5', ]
		self.shlex_active = False

		# each command line is prefixed by this string
		self.PS1 = "cmd % "

		# output streams
		self.stdout = sys.stdout.write
		self.stderr = sys.stderr.write

		self._create_command_table()

		self._usage_dict      = dict()
		self._current_command = None

		# the command table of exit commands
		#  each listed command can be used to exit the depres console
		self.cmd_exit = frozenset (( 'q', 'qq', 'exit' ))

		if sys.version_info < ( 3, 0 ):
			self._get_input = raw_input
		else:
			self._get_input = input
	# --- end of __init__ (...) ---

	def _getpool ( self, new=False ):
		"""Returns a dependency rule pool. Creates a new one if no pool exists
		or 'new' is set to True.

		arguments:
		* new -- defaults to True
		"""
		if not self.poolstack or ( new and not self.poolstack [-1].empty() ):
			pool = SimpleDependencyRulePool (
				"pool" + str ( self.pool_id ),
				deptype_mask=deptype.RESOLVE_ALL
			)
			self.pool_id += 1
			self.poolstack.append ( pool )
			self.resolver._reset_unresolvable()

		return self.poolstack [-1]
	# --- end of _getpool (...) ---

	def cmd_mkhelp ( self, argv, line ):
		missing = list()
		for cmd in self.cmd_table:
			try:
				self._get_usage ( cmd )
			except KeyError:
				missing.append ( cmd )

		if missing:
			print (
				"Please write help messages for the following commands: " + \
					', '.join ( sorted ( missing ) )
			)
			return False
		else:
			print ( "Everything looks ok." )
			return True
	# --- end of cmd_mkhelp (...) ---

	def cmd_cd ( self, argv, line ):
		if argv:
			self._cwd = os.path.abspath ( os.path.expanduser ( argv [0] ) )
			if not os.path.isdir ( self._cwd ):
				os.makedirs ( self._cwd )
			self.stdout ( "cwd = {!r}\n".format ( self._cwd ) )
			return True
		else:
			return self.usage()
	# --- end of cmd_cd (...) ---

	def cmd_rule_scandir ( self, argv, line ):
		"""Scans a directory for R packages and creates rules for them.

		Usage: scandir <directory>
		"""
		if argv and os.path.isdir ( argv[0] ):
			pool = self._getpool ( new=True )
			self.stdout ( "new rules:\n" )
			for r in self._dir_rule_maker.make_rules ( argv [0] ):
				self.stdout ( str ( r ) + "\n" )
				pool.add ( r )
			self.stdout ( "--- ---\n" )
			pool.sort()

		else:
			self.stderr ( "arg0 is not a dir\n" )
			return self.usage()
	# --- end of cmd_rule_scandir (...) ---

	def cmd_rule_load_from_config ( self, argv, line ):
		load = config.get_or_fail ( "DEPRES.simple_rules.files" )
		self.resolver.get_reader().read ( load )
		# don't write into ^this pool
		self._getpool ( new=True )
	# --- end of cmd_rule_load_from_config (...) ---

	def cmd_rule_load ( self, argv, line ):
		if argv:
			self.resolver.get_reader().read ( argv )
		else:
			return self.usage()
	# --- end of cmd_rule_load (...) ---

	def cmd_rule_add ( self, argv, line ):
		if not line:
			return self.usage()
		elif self._rule_maker.add ( line ):
			rules = self._rule_maker.done()
			pool  = self._getpool()

			self.stdout ( "new rules:\n" )
			for _deptype, r in rules:
				self.stdout ( str ( r ) + "\n" )
				pool.rules.append ( r )
			self.stdout ( "--- ---\n" )

			pool.sort()

			self.resolver._reset_unresolvable()

			return True
		else:
			return False
	# --- end of cmd_addrule (...) ---

	def cmd_pool_print ( self, argv, line ):
		if argv and len ( argv ) > 0:
			if argv[0] == "all":
				_last = len ( self.poolstack )
				for n, p in enumerate ( self.poolstack ):
					self.stdout ( "showing pool {}/{}.\n".format (
						n + 1, _last
					))
					p.export_rules ( sys.stdout )
			else:
				self.stdout ( "unknown arg1 {!r}.\n".format ( argv[0] ) )
				return self.usage()
		else:
			if len ( self.poolstack ):
				self.poolstack [-1].export_rules ( sys.stdout )
	# --- end of cmd_pool_print (...) ---

	def cmd_pool_write ( self, argv, line ):
		if not argv:
			return self.usage()

		if argv[0][0] == os.sep:
			f = argv [0]
		elif self._cwd is not None:
			f = self._cwd + os.sep + argv [0]
		else:
			f = os.path.abspath ( argv[0] )

		if os.access ( f, os.F_OK ):
			self.stdout ( "file {!r} exists!\n".format ( f ) )
			return False

		elif len ( self.poolstack ):
			try:
				fh = open ( f, 'w' )
				self.poolstack[-1].export_rules ( fh )
				fh.close()
				self.stdout ( "Wrote {!r}.\n".format ( f ) )
				return True
			finally:
				if 'fh' in locals() and fh: fh.close()

		else:
			self.stdout ( "no pool in use.\n" )
			return False
	# --- end of cmd_pool_write (...) ---


	def cmd_pool_unwind ( self, argv, line ):
		if self.poolstack:
			self.poolstack.pop()
			self.stdout ( "Pool removed from resolver.\n" )
		else:
			self.stdout ( "Resolver has no pools.\n" )
	# --- end of cmd_pool_unwind (...) ---

	def cmd_pool_add ( self, argv, line ):
		self._getpool ( new=True )
		self.stdout ( "New pool created.\n" )
	# --- end of cmd_pool_add (...) ---

	def run ( self ):
		cmd = None

		self.stdout (
			'== depres console ==\n'
			'Run \'help\' to list all known commands\n'
			'More specifically, \'help <cmd>\' prints a help message for the '
			'given command, and \'help --list\' lists all help topics available\n'
			'Use \'load_conf\' or \'lc\' to load the configured rule files\n'
		)
		if self.shlex_active:
			self.stdout (
				'Note: shlex mode is enabled by default. '
				'This splits all args according to shell syntax. '
				'You can disable this (useful when resolving) '
				'with \'unset shlex\'.\n'
			)
		self.stdout ( "\n" )
		self.cmd_help()
		self.stdout ( "\n" )

		while True:
			try:
				#self.stdout ( "\n" )
				cmd, argv, line = self.split_line ( self._get_input ( self.PS1 ) )

				if cmd is None:
					pass
				elif cmd in self.cmd_exit:
					break
				elif cmd in self.cmd_table:
					self._current_command = cmd
					ret = self.cmd_table [cmd] ( argv=argv, line=line )
					if ret is True:
						self.stdout ( "command succeeded.\n" )
					elif ret is False:
						self.stdout ( "command failed.\n" )
				else:
					self.stdout ( "command {!r} not found.\n".format ( cmd ) )
					self.cmd_help()

			except KeyboardInterrupt:
				self.stdout ( "\nuse \'exit\' to exit (or close stdin)\n" )
			except EOFError:
				self.stderr ( "\nexiting...\n" )
				break
			except Exception as e:
				logging.exception ( e )
				self.stderr ( str ( e ) + "\n" )

		self.resolver.close()
	# --- end of run (...) ---

	def split_line ( self, line ):
		l = line.strip()
		if not l:
			return ( None, None, None )

		linev = self.__class__.whitespace.split ( l, 1 )

		if len ( linev ) == 0:
			return ( None, None, None )
		elif len ( linev ) == 1:
			return ( linev [0].lower(), None, None )
		elif self.shlex_active:
			return ( linev [0].lower(), shlex.split ( linev [1] ), linev [1] )
		else:
			return ( linev [0].lower(), ( linev [1], ), linev [1] )
	# --- end of split_line (...) ---

	def cmd_help ( self, argv=None, *ignored, **kwargs_ignored ):
		if argv:
			if argv [0] == '--list':
				print (
					"The following help topics are available: " + \
					', '.join ( self.__class__.CMD_USAGE ) + "."
				)
			else:
				for cmd in argv:
					self._print_usage ( cmd )
		else:
			self.stdout ( "commands: {}\n".format (
				', '.join ( self.cmd_table.keys() )
			) )
			self.stdout ( "exit-commands: {}\n".format (
				', '.join ( self.cmd_exit )
			) )
	# --- end of cmd_help (...) ---

	def cmd_resolve ( self, argv, line ):
		dep_list = argv
		if not dep_list:
			self.stdout ( "Resolve what?\n" )
			return self.usage()
		else:
			channel = EbuildJobChannel (
				err_queue=self.err_queue, name="channel"
			)
			self.resolver.register_channel ( channel )

			self.stdout ( "Trying to resolve {!r}.\n".format ( dep_list ) )

			channel.add_dependencies ( dep_list, deptype.ALL )
			deps = channel.satisfy_request (
				close_if_unresolvable=False,
				preserve_order=True
			)
			channel.close()

			if deps is None:
				self.stdout (
					'Channel returned None. '
					'At least one dep couldn\'t be resolved.\n'
			)
			else:
				self.stdout ( "Resolved as: {!r}\n".format ( deps [0] ) )
	# --- end of cmd_resolve (...) ---

	def _cmd_set_or_unset ( self, argv, is_set ):
		if not argv:
			self.stdout ( "shlex mode is {}.\n".format (
				"on" if self.shlex_active else "off"
			) )
		elif argv [0] == 'shlex':
			self.shlex_active = is_set
		elif argv [0].lower() == "ps1":
			if is_set:
				self.PS1 = argv [1] + ' '
			else:
				self.PS1 = "cmd % "
		else:
			self.stdout ( "unknown args: {}.\n".format ( argv ) )
			return self.usage()
	# --- end of _cmd_set_or_unset (...) ---

	def cmd_set ( self, argv, line ):
		self._cmd_set_or_unset ( argv, True )
	# --- end of cmd_set (...) ---

	def cmd_unset ( self, argv, line ):
		self._cmd_set_or_unset ( argv, False )
	# --- end of cmd_unset (...) ---
