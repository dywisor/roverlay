#!/usr/bin/env python

import sys

# other roverlay modules will be imported later
import roverlay

HIDE_EXCEPTIONS = False

def die ( msg=None, code=1 ):
	if msg:
		sys.stderr.write ( msg + "\n" )
	sys.exit ( code )


if __name__ != '__main__':
	die ( "Please don't import this script..." )


# get args
import roverlay.argutil

COMMAND_DESCRIPTION = {
	'sync'           : 'sync repos',
	'create'         : 'create the overlay',
#	'depres_console' : 'run an interactive depres console; TODO/REMOVE',
	'nop'            : 'does nothing',
}

commands, config_file, additional_config, extra_opts = \
	roverlay.argutil.parse_argv (
		CMD_DESC=COMMAND_DESCRIPTION,
		DEFAULT_CONFIG="R-overlay.conf"
	)
del roverlay.argutil

# -- load config
try:
	roverlay.load_config_file ( config_file, extraconf=additional_config )
	del config_file, additional_config
except:
	if HIDE_EXCEPTIONS:
		die ( "Cannot load config file %r." % config_file )
	else:
		raise

# -- determine commands to run
# (TODO) could replace this section when adding more actions

actions = set ( filter ( lambda x : x != 'nop', commands ) )

if 'sync' in actions and extra_opts ['nosync']:
	die ( "sync command blocked by --nosync opt." )

del commands


if not actions:
	# this happens if a command is nop
	die ( "Nothing to do!", 0 )


# -- import roverlay modules

from roverlay.remote          import RepoList
from roverlay.overlay.creator import OverlayCreator


# -- run

actions_done = list()

### sync / nosync
# always run 'cause commands = {create,sync} and create implies (no)sync

# set up the repo list
repo_list = RepoList ( sync_enabled=not extra_opts ['nosync'] )

## extra_opts->distdir ... TODO
repo_list.load()

## this runs _nosync() or _sync(), depending on extra_opts->nosync
repo_list.sync()

if 'sync' in actions:
	actions_done.append ( 'sync' )

###

# run overlay creation

if 'create' in actions:
	try:
		overlay = OverlayCreator()
		overlay.can_write_overlay = extra_opts ['write']

		repo_list.add_packages ( overlay.add_package )

		overlay.run()

		if extra_opts ['show']:
			overlay.show_overlay()

		if overlay.can_write_overlay:
			overlay.write_overlay()

		# write overlay on close
		overlay.close()

		actions_done.append ( 'create' )

	except:
		if HIDE_EXCEPTIONS:
			die ( "Overlay creation failed.", 15 )
		else:
			raise


if len ( actions ) != len ( actions_done ):
	die ( "Some actions (out of %r) could not be performed!" % actions, 90 )
