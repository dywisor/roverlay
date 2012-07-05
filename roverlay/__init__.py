# R Overlay
# Copyright 2006-2012 Gentoo Foundation
# Distributed under the terms of the GNU General Public License v2
import roverlay.config
import roverlay.recipe.easylogger

name = "R_overlay"
version = ( 0, 0, 1 )
version_str = '.'.join ( ( str ( i ) for i in version ) )
description_str = "R overlay creation " + version_str
license_str     = '\n'.join ((
	'Copyright <fixthis>',
	'Distributed under the terms of the GNU General Public License v2',
))


roverlay.recipe.easylogger.setup_initial()

def load_config_file ( cfile, extraconf=None ):
	"""
	Loads the config, including the field definition file.
	Sets up the logger afterwards.
	(Don't call this method more than once.)

	arguments:
	* cfile     -- path to the config file
	* extraconf -- a dict with additional config entries that will override
	               entries read from cfile
	"""
	roverlay.config.loader().load_config ( cfile )

	if extraconf is not None:
		roverlay.config.access().merge_with ( extraconf )

	roverlay.recipe.easylogger.setup ( roverlay.config.access() )

	fdef_f = config.get_or_fail ( "DESCRIPTION.field_definition_file" )
	roverlay.config.loader().load_field_definition ( fdef_f )

	return config.access()
