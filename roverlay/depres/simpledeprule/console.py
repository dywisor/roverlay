import re
import os
import sys
import shlex
import logging

from roverlay import config, strutil
from roverlay.errorqueue                     import ErrorQueue
from roverlay.depres                         import deptype
from roverlay.depres.depresolver             import DependencyResolver
from roverlay.depres.channels                import EbuildJobChannel
from roverlay.depres.simpledeprule.pool      import SimpleDependencyRulePool
from roverlay.depres.simpledeprule.rulemaker import SimpleRuleMaker

from roverlay.depres.simpledeprule import rules
class PackageDirRuleMaker ( object ):
	"""Scans a distdir and creates selfdep rules for it.
	Part of the console module 'cause only used here (currently).
	"""

	def __init__ ( self, fuzzy=True ):
		self.fuzzy = fuzzy
		self.package_regex = re.compile (
			"^(?P<name>[^_]+)_.+{}$".format (
				config.get_or_fail ( 'R_PACKAGE.suffix_regex' )
			)
		)
	# --- end of __init__ (...) ---

	def _scan ( self, distdir ):
		# ~duplicate of remote/basicrepo

		for dirpath, dirnames, filenames in os.walk ( distdir ):
			for filename in filenames:
				m = self.package_regex.match ( filename )
				if m is not None:
					yield m.group ( 'name' )
	# --- end of _scan (...) ---

	def make_rules ( self, distdir ):
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

	shlex = shlex.shlex()
	whitespace = re.compile ( "\s+" )

	def __init__ ( self ):
		self.err_queue = ErrorQueue()

		self.resolver = DependencyResolver ( err_queue=self.err_queue )
		# log everything
		self.resolver.set_logmask ( -1 )
		# disable passing events to listeners
		self.resolver.set_listenermask ( 0 )

		self.poolstack = self.resolver.static_rule_pools
		self.pool_id   = 0

		self._rule_maker = SimpleRuleMaker()
		self._dir_rule_maker = PackageDirRuleMaker()

		self._cwd = None

		self.shlex_active = True

		self.PS1 = "cmd % "

		self.stdout = sys.stdout.write
		self.stderr = sys.stderr.write

		self.cmd_table = {
			'resolve'   : self.cmd_resolve,
			'r'         : self.cmd_resolve,
			'?'         : self.cmd_resolve,
			'scandir'   : self.cmd_rule_scandir,
			'sd'        : self.cmd_rule_scandir,
			'addrule'   : self.cmd_rule_add,
			'+'         : self.cmd_rule_add,
			'load'      : self.cmd_rule_load,
			'li'        : self.cmd_rule_load,
			'l'         : self.cmd_rule_load,
			'load_conf' : self.cmd_rule_load_from_config,
			'lc'        : self.cmd_rule_load_from_config,
			'pool'      : self.cmd_pool,
			'write'     : self.cmd_pool_write,
			'w'         : self.cmd_pool_write,
			'p'         : self.cmd_pool_print,
			'print'     : self.cmd_pool_print,
			'unwind'    : self.cmd_pool_unwind,
			'>>'        : self.cmd_pool_unwind,
			'add_pool'  : self.cmd_pool_add,
			'<<'        : self.cmd_pool_add,
			'cd'        : self.cmd_cd,
			'set'       : self.cmd_set,
			'unset'     : self.cmd_unset,
			'help'      : self.cmd_help,
		}

		self.cmd_exit = frozenset (( 'q', 'qq', 'exit' ))

		if sys.version_info < ( 3, 0 ):
			self._get_input = raw_input
		else:
			self._get_input = input
	# --- end of __init__ (...) ---

	def _getpool ( self, new=False ):
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

	def cmd_cd ( self, argv, line ):
		if not argv:
			self.stdout (
				"usage is cd <dir>, dir will be created if not existent.\n"
			)
			return False
		else:
			self._cwd = os.path.abspath ( argv [0] )
			if not os.path.isdir ( self._cwd ):
				os.makedirs ( self._cwd )
			self.stdout ( "cwd = {!r}\n".format ( self._cwd ) )
			return True
	# --- end of cmd_cd (...) ---

	def cmd_rule_scandir ( self, argv, *ignored ):
		if not argv:
			self.stdout ( "usage is scandir <dir>\n" )
			return False
		elif not os.path.isdir ( argv[0] ):
			self.stderr ( "arg0 is not a dir\n" )
			return False

		pool = self._getpool ( new=True )
		self.stdout ( "new rules:\n" )
		for r in self._dir_rule_maker.make_rules ( argv [0] ):
			self.stdout ( str ( r ) + "\n" )
			pool.add ( r )
		self.stdout ( "--- ---\n" )
		pool.sort()

	def cmd_rule_load_from_config ( self, *ignored ):
		load = config.get_or_fail ( "DEPRES.simple_rules.files" )
		self.resolver.get_reader().read ( load )
		# don't write into ^this pool
		self._getpool ( new=True )
	# --- end of cmd_rule_load_from_config (...) ---

	def cmd_rule_load ( self, argv, line ):
		if argv:
			self.resolver.get_reader().read ( argv )
		else:
			self.stdout ( "usage is load/li <files or dirs>\n" )
	# --- end of cmd_rule_load (...) ---

	def cmd_rule_add ( self, argv, line ):
		if not line:
			self.stdout ( "usage is <cmd> <rule>\n" )
		elif self._rule_maker.add ( line ):
			rules = self._rule_maker.done()
			pool = self._getpool()

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

	def cmd_pool_help ( self, *ignore ):
		self.stdout ( "<todo>\n" )
	# --- end of cmd_pool_help (...) ---

	def cmd_pool_print ( self, argv, *ignore ):
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
				return False
		else:
			if len ( self.poolstack ):
				self.poolstack [-1].export_rules ( sys.stdout )
	# --- end of cmd_pool_print (...) ---

	def cmd_pool ( self, argv, line ):
		if not argv:
			self.stdout ( "usage: pool <action> [args]\n" )
			return self.cmd_pool_help()

		cmd = argv[0]

		if cmd == "unwind" or cmd == "destroy":
			return self.cmd_pool_unwind ( argv, line )
		elif cmd == "add" or cmd == "create":
			return self.cmd_pool_add ( argv, line )
		elif cmd == "print" or cmd == "show":
			if len ( argv ) > 1:
				return self.cmd_pool_print ( argv[1:] )
			else:
				return self.cmd_pool_print ( None )

	# --- end of cmd_pool (...) ---

	def cmd_pool_write ( self, argv, *ignore ):
		if not argv:
			self.stdout ( "usage: write <file>\n" )
			return False

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


	def cmd_pool_unwind ( self, *ignore ):
		if self.poolstack:
			self.poolstack.pop()
			self.stdout ( "Pool removed from resolver.\n" )
		else:
			self.stdout ( "Resolver has no pools.\n" )
	# --- end of cmd_pool_unwind (...) ---

	def cmd_pool_add ( self, *ignore ):
		self._getpool ( new=True )
		self.stdout ( "New pool created.\n" )
	# --- end of cmd_pool_add (...) ---

	def run ( self ):
		cmd = None

		self.stdout (
			'== depres console ==\n'
			'run \'help\' to list all known commands\n'
			'use \'load_conf\' or \'lc\' to load the configured rule files\n'
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
					ret = self.cmd_table [cmd] ( argv, line )
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

	def cmd_help ( self, *ignored ):
		self.stdout ( "commands: {}\n".format (
			', '.join ( self.cmd_table.keys() )
		) )
		self.stdout ( "exit-commands: {}\n".format (
			', '.join ( self.cmd_exit )
		) )
	# --- end of cmd_help (...) ---

	def cmd_resolve ( self, dep_list, line ):
		if not dep_list:
			self.stdout ( "Resolve what?\n" )
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
					'Channel returned {!r}. '
					'At least one dep couldn\'t be resolved.\n'.format ( deps )
			)
			else:
				self.stdout ( "Resolved as: {!r}\n".format ( deps ) )
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
	# --- end of _cmd_set_or_unset (...) ---

	def cmd_set ( self, argv, line ):
		self._cmd_set_or_unset ( argv, True )
	# --- end of cmd_set (...) ---

	def cmd_unset ( self, argv, line ):
		self._cmd_set_or_unset ( argv, False )
	# --- end of cmd_unset (...) ---
