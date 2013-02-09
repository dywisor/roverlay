# R overlay -- main()
# -*- coding: utf-8 -*-
# Copyright (C) 2012 André Erdmann <dywi@mailerd.de>
# Distributed under the terms of the GNU General Public License;
# either version 2 of the License, or (at your option) any later version.

"""main script for R overlay creation"""

__all__ = [ 'main' ]

import os
import sys
import time

# roverlay modules will be imported later

DEFAULT_CONFIG_FILE_NAME = "R-overlay.conf"

# directories where the config file could be found if roverlay has been
# installed, in order:
# * ${PWD}
# * user roverlay dir (${HOME}/roverlay)
# * system config dir /etc/roverlay
CONFIG_DIRS = tuple ((
	'.',
	(
		( os.getenv ( 'HOME' ) or os.path.expanduser ( '~' ) )
		+ os.sep + 'roverlay'
	),
	# os.sep is '/' if /etc exists, so don't care about that
	'/etc/roverlay',
))


class DIE ( object ):
	"""Container class for various system exit 'events'."""
	NOP          =  os.EX_OK
	ERR          =  1
	BAD_USAGE    =  os.EX_USAGE
	USAGE        =  os.EX_USAGE
	ARG          =  9
	CONFIG       =  os.EX_CONFIG
	OV_CREATE    =  20
	SYNC         =  30
	CMD_LEFTOVER =  90
	IMPORT       =  91
	UNKNOWN      =  95
	INTERRUPT    = 130

	@staticmethod
	def die ( msg=None, code=None ):
		"""
		Calls syst.exit (code:=DIE.ERR) after printing a message (if any).
		"""
		code = DIE.ERR if code is None else code
		if msg is not None:
			sys.stderr.write ( msg + "\n" )
#		else:
#			sys.stderr.write ( "died.\n" )
		sys.exit ( code )
	# --- end of die (...) ---

# --- DIE: exit codes ---
die = DIE.die

def main (
	ROVERLAY_INSTALLED,
	HIDE_EXCEPTIONS=False,
	CONFIG_FILE_NAME=DEFAULT_CONFIG_FILE_NAME
):
	"""main() - parse args, run overlay creation, sync, ...

	arguments:
	* ROVERLAY_INSTALLED -- whether roverlay has been installed or not
	* HIDE_EXCEPTIONS    -- hide exceptions? (optional, defaults to False)
	* CONFIG_FILE_NAME   -- name of the config file (optional, defaults to
	                        "R-overlay.conf")
	"""
	def optionally ( call, option, *args, **kw ):
		if OPTION ( option ):
			return call ( *args, **kw )
	# --- end of optionally (...) ---

	def run_sync():
		if "sync" in actions_done: return
		try:
			# set up the repo list
			global repo_list
			repo_list = RepoList (
				sync_enabled   = not OPTION ( 'nosync' ),
				force_distroot = OPTION ( 'force_distroot' )
			)

			## extra_opts->distdir
			if 'distdirs' in extra_opts:
				repo_list.add_distdirs ( OPTION ( 'distdirs' ) )
			else:
				# default repo list
				repo_list.load()

			## this runs _nosync() or _sync(), depending on extra_opts->nosync
			t_start = time.time()
			repo_list.sync()
			global sync_time
			sync_time = time.time() - t_start

			set_action_done ( "sync" )

		except KeyboardInterrupt:
			die ( "Interrupted", DIE.INTERRUPT )
		except:
			if HIDE_EXCEPTIONS:
					die (
						"nosync() failed!" if OPTION ( "nosync" ) \
							else "sync() failed!",
						DIE.SYNC
					)
			else:
				raise
	# --- end of run_sync() ---

	def run_overlay_create():
		if "create" in actions_done: return
		#run_sync()
		try:
			global overlay_creator
			overlay_creator = OverlayCreator (
				skip_manifest           = OPTION ( 'skip_manifest' ),
				incremental             = OPTION ( 'incremental' ),
				allow_write             = OPTION ( 'write_overlay' ),
				immediate_ebuild_writes = OPTION ( 'immediate_ebuild_writes' ),
			)

			if 'sync_time' in globals():
				overlay_creator.set_timestats ( 'sync_packages', sync_time )

			t_start = time.time()
			repo_list.add_packages ( overlay_creator.add_package )
			overlay_creator.set_timestats (
				'add_packages', time.time() - t_start
			)

			overlay_creator.run ( close_when_done=True )

			optionally ( overlay_creator.write_overlay, 'write_overlay' )
			optionally ( overlay_creator.show_overlay,  'show_overlay'  )
			if OPTION ( 'print_stats' ):
				print ( "\n" + overlay_creator.stats_str() )

			set_action_done ( "create" )

		except KeyboardInterrupt:
			die ( "Interrupted", DIE.INTERRUPT )
		except:
			if HIDE_EXCEPTIONS:
				die ( "Overlay creation failed.", DIE.OV_CREATE )
			else:
				raise
		finally:
			if 'overlay_creator' in locals() and not overlay_creator.closed:
				# This is important 'cause it unblocks remaining ebuild creation
				# jobs/threads, specifically waiting EbuildJobChannels in depres.
				# It also writes the deps_unresolved file
				overlay_creator.close()
	# --- end of run_overlay_create() ---

	# get args
	# imports roverlay.argutil (deleted when done)
	try:
		import roverlay.argutil
	except ImportError:
		if HIDE_EXCEPTIONS:
			die ( "Cannot import roverlay modules!", DIE.IMPORT )
		else:
			raise

	COMMAND_DESCRIPTION = {
		'sync'           : 'sync repos',
		'create'         : 'create the overlay '
								  '(implies sync, override with --nosync)',
		'depres_console' : \
			'run an interactive depres console (highly experimental)',
		'depres'         : 'this is an alias to \'depres_console\'',
		'nop'            : 'does nothing',
	}


	DEFAULT_CONFIG_FILE = None
	# search for the config file if roverlay has been installed
	if ROVERLAY_INSTALLED:
		cfg        = None
		config_dir = None

		for config_dir in CONFIG_DIRS:
			cfg = config_dir + os.sep + CONFIG_FILE_NAME
			if os.path.isfile ( cfg ):
				DEFAULT_CONFIG_FILE = cfg
				break

		del config_dir, cfg
	elif os.path.exists ( CONFIG_FILE_NAME ):
		DEFAULT_CONFIG_FILE = CONFIG_FILE_NAME


	commands, config_file, additional_config, extra_opts = \
		roverlay.argutil.parse_argv (
			command_map=COMMAND_DESCRIPTION,
			default_config_file=DEFAULT_CONFIG_FILE,
		)

	OPTION = extra_opts.get

	del roverlay.argutil

	# -- determine commands to run
	# (TODO) could replace this section when adding more actions
	# imports roverlay.remote, roverlay.overlay.creator

	actions = set ( filter ( lambda x : x != 'nop', commands ) )

	if 'sync' in actions and OPTION ( 'nosync' ):
		die ( "sync command blocked by --nosync opt.", DIE.ARG )

	del commands


	if not actions:
		# this happens if a command is nop
		die ( "Nothing to do!", DIE.NOP )

	# -- load config

	# imports: roverlay, roverlay.config.entryutil (if --help-config)

	try:
		import roverlay
	except ImportError:
		if HIDE_EXCEPTIONS:
			die ( "Cannot import roverlay modules!", DIE.IMPORT )
		else:
			raise

	try:
		roverlay.setup_initial_logger()

		conf = roverlay.load_config_file (
			config_file,
			extraconf=additional_config
		)
		del config_file, additional_config
	except:
		if not config_file:
			sys.stderr.write ( '!!! No config file found.\n' )

		if HIDE_EXCEPTIONS:
			die (
				"Cannot load config file {!r}.".format ( config_file ), DIE.CONFIG
			)
		else:
			raise

	if OPTION ( 'list_config' ):
		try:
			from roverlay.config.entryutil import list_entries
			print ( "== main config file ==\n" )
			print ( list_entries() )
		except:
			raise
			die ( "Cannot list config entries!" )

		EXIT_AFTER_CONFIG = True

	if OPTION ( 'print_config' ):
		try:
			conf.visualize ( into=sys.stdout )
		except:
			die ( "Cannot print config!" )
		EXIT_AFTER_CONFIG = True

	if OPTION ( 'print_package_rules' ):
		# no try-/catch block here

		import roverlay.packagerules.rules

		HLINE = "".rjust ( 79, '-' )
		print ( HLINE )
		print (
			str ( roverlay.packagerules.rules.PackageRules.get_configured() )
		)
		print ( HLINE )

		EXIT_AFTER_CONFIG = True

	# -- end of EXIT_AFTER_CONFIG entries

	if 'EXIT_AFTER_CONFIG' in locals() and EXIT_AFTER_CONFIG:
		pass
		#sys.exit ( os.EX_OK )

	# switch to depres console
	elif 'depres_console' in actions or 'depres' in actions:
		if len ( actions ) != 1:
			die ( "depres_console cannot be run with other commands!", DIE.USAGE )

		try:
			from roverlay.depres.simpledeprule.console import DepResConsole
			con = DepResConsole()
			con.run()
			sys.exit ( os.EX_OK )
		except ImportError:
			if HIDE_EXCEPTIONS:
				die ( "Cannot import depres console!", DIE.IMPORT )
			else:
				raise
		except:
			if HIDE_EXCEPTIONS:
				die ( "Exiting on console error!", DIE.ERR )
			else:
				raise

	else:
		# sync/create
		# -- import roverlay modules

		try:
			from roverlay.remote          import RepoList
			from roverlay.overlay.creator import OverlayCreator
		except ImportError:
			if HIDE_EXCEPTIONS:
				die ( "Cannot import roverlay modules!", DIE.IMPORT )
			else:
				raise

		# -- run methods (and some vars)
		# imports: nothing

		#repo_list       = None
		#overlay_creator = None

		actions_done = set()
		set_action_done = actions_done.add

		# -- run

		# always run sync 'cause commands = {create,sync}
		# and create implies (no)sync
		run_sync()

		if 'create' in actions: run_overlay_create()

		if len ( actions ) > len ( actions_done ):
			die (
				"Some actions (out of {!r}) could not be performed!".format (
					actions ), DIE.CMD_LEFTOVER
			)
# --- end of main (...) ---