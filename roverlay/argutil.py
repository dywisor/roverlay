# R overlay -- roverlay package, argutil
# -*- coding: utf-8 -*-
# Copyright (C) 2012 André Erdmann <dywi@mailerd.de>
# Distributed under the terms of the GNU General Public License;
# either version 2 of the License, or (at your option) any later version.

"""provides arg parsing for the roverlay main script"""

__all__ = [ 'parse_argv', ]

import os.path
import argparse
import roverlay

def get_parser ( command_map, default_config_file, default_command='create' ):
	"""Returns an arg parsers.

	arguments:
	* command_map         -- a dict ( <command> => <command description> )
	* default_config_file -- the default config file (for --config)
	* default_command     -- the default command
	"""

	def is_fs_file ( value ):
		f = os.path.abspath ( value )
		if not os.path.isfile ( f ):
			raise argparse.ArgumentTypeError (
				"{!r} is not a file.".format ( value )
			)
		return f

	def is_fs_dir ( value ):
		d = os.path.abspath ( value )
		if not os.path.isdir ( d ):
			raise argparse.ArgumentTypeError (
				"{!r} is not a directory.".format ( value )
			)
		return d

	def is_fs_file_or_dir ( value ):
		f = os.path.abspath ( value )
		if os.path.isdir ( f ) or os.path.isfile ( f ):
			return f
		else:
			raise argparse.ArgumentTypeError (
				"{!r} is neither a file nor a directory.".format ( value )
			)

	def couldbe_fs_dir ( value ):
		d = os.path.abspath ( value )
		if os.path.exists ( d ) and not os.path.isdir ( d ):
			raise argparse.ArgumentTypeError (
				"{!r} cannot be a directory.".format ( value )
			)
		return d

	def is_fs_file_or_void ( value ):
		if value:
			return is_fs_file ( value )
		else:
			return ''

	parser = argparse.ArgumentParser (
		description='\n'.join ((
			roverlay.description_str, roverlay.license_str,
		)),
		epilog = 'Known commands:\n' + '\n'.join (
			(
				# '* <space> <command> - <command description>'
				'* {cmd} - {desc}'.format (
					cmd  = i [0].ljust ( 15 ),
					desc = i [1]
				) for i in command_map.items()
			)
		),
		add_help=True,
		formatter_class=argparse.RawDescriptionHelpFormatter,
		)

	arg     = parser.add_argument
	opt_in  = dict ( default=False, action='store_true' )
	opt_out = dict ( default=True,  action='store_false' )

	fs_file = dict ( type=is_fs_file, metavar="<file>" )

	# adding args starts here

	arg (
		'-V', '--version', action='version', version=roverlay.__version__
	)

	arg (
		'commands',
		default=default_command,
		help="action to perform. choices are " + ', '.join (command_map.keys()) \
		+ ". defaults to %(default)s.",
		nargs="*",
		choices=command_map.keys(),
		metavar="command"
	)

	arg (
		'-c', '--config',
		default=default_config_file,
		help="config file",
		type=is_fs_file_or_void, metavar="<file>"
	)
	arg (
		'-F', '--field-definition', '--fdef', default=argparse.SUPPRESS,
		help="field definition file",
		**fs_file
	)

	arg (
		'-R', '--repo-config', default=argparse.SUPPRESS,
		action='append',
		help="repo config file.",
		**fs_file
	)

	arg (
		'-D', '--deprule-file', default=argparse.SUPPRESS,
		action='append',
		help="simple rule file. can be specified more than once.",
		type=is_fs_file_or_dir,
		metavar='<file|dir>',
	)

	arg (
		'--distdir', '--from', default=argparse.SUPPRESS,
		action='append',
		help='''
			use packages from %(metavar)s for ebuild creation (ignore all repos).
			only useful for testing 'cause SRC_URI will be invalid in the created
			ebuilds.
		''',
		metavar="<DISTDIR>",
		dest='distdirs',
		type=is_fs_dir
	)

	arg (
		'--distroot', default=argparse.SUPPRESS,
		help='''
			use %(metavar)s as distdir root for repos
			that don't define their own package dir.
		''',
		metavar="<DISTROOT>",
		type=couldbe_fs_dir
	)

	arg (
		'--overlay', '-O', default=argparse.SUPPRESS,
		help='overlay directory to write (implies --write)',
		metavar="<OVERLAY>",
		type=couldbe_fs_dir
	)

	arg (
		'--overlay-name', '-N', default=argparse.SUPPRESS,
		help="overlay name",
		metavar="<name>",
		dest="overlay_name"
	)

	arg (
		'--show-overlay', '--show',
		help="print ebuilds and metadata to console",
		dest="show_overlay",
		default=False,
		action="store_true",
	)

	arg (
		'--no-show-overlay', '--no-show',
		help="don't print ebuilds and metadata to console (default)",
		dest="show_overlay",
		action="store_false",
	)

	arg (
		'--write-overlay', '--write',
		help="write the overlay to filesystem",
		dest="write_overlay",
		default=True,
		action="store_true",
	)

	arg (
		'--no-write-overlay', '--no-write',
		help="don't write the overlay",
		dest="write_overlay",
		action="store_false",
	)

	arg (
		'--immediate-ebuild-writes',
		help='write ebuilds as soon as they\'re ready, '
			'which saves memory but costs more time',
		dest='immediate_ebuild_writes',
		default=False,
		action='store_true',
	)

	arg (
		'--stats',
		help="print some stats",
		dest="stats",
		default=True,
		action="store_true",
	)

	arg (
		'--no-stats',
		help="don't print stats",
		dest="stats",
		action="store_false",
	)

	arg (
		'--nosync', '--no-sync',
		help="disable syncing with remotes (offline mode).",
		**opt_in
	)

	arg (
		'--force-distroot',
		help="always use <DISTROOT>/<repo name> as repo distdir.",
		**opt_in
	)

	arg (
		'--print-config', '--pc',
		help="print config and exit",
		**opt_in
	)

	arg (
		'--list-config-entries', '--help-config',
		help="list all known config entries",
		**opt_in
	)

	# --write-desc
	# --log-level, --log-console, --log...

	arg (
		'--no-manifest',
		help="skip Manifest creation (results in useless overlay)",
		**opt_in
	)

	arg (
		'--manifest-implementation', '-M', default=argparse.SUPPRESS,
		help="choose how Manifest files are written (ebuild(1) or portage libs)",
		metavar="<impl>",
		choices=frozenset (( 'ebuild', 'e', 'portage', 'p' )),
	)

	# FIXME: description of --no-incremental is not correct,
	# --no-incremental currently means that an existing overlay won't be
	# scanned for ebuilds (which means that ebuilds will be recreated),
	# but old ebuilds won't be explicitly removed
	arg (
		'--no-incremental',
		help="start overlay creation from scratch (ignore an existing overlay)",
		dest='incremental',
		default=True,
		action='store_false',
	)

#	# TODO
#	arg (
#		'--debug',
#		help='''
#			Turn on debugging. This produces a lot of messages.
#			(TODO: has no effect).
#		''',
#		**opt_in
#	)

	return parser
# --- end of get_parser (...) ---

def parse_argv ( command_map, **kw ):
	"""Parses sys.argv and returns the result as tuple
	(<commands to run>, <config file>,
	<dict for config>, <extra options as dict>).

	All args/keywords are passed to get_parser().
	Passes all exceptions.
	"""
	def doconf ( value, path ):
		pos = conf
		if isinstance ( path, str ):
			path = path.split ( '.' )
		last = len ( path ) - 1
		for i, k in enumerate ( path ):
			if i == last:
				pos [k.lower()] = value
			else:
				k = k.upper()
				if not k in pos:
					pos [k] = dict()

				pos = pos [k]


	p = get_parser ( command_map=command_map, **kw ).parse_args()

	given = lambda kw : hasattr ( p, kw )

	commands = ( p.commands, ) if isinstance ( p.commands, str ) else p.commands
	conf  = dict()
	extra = dict (
		nosync                  = p.nosync,
#		debug                   = p.debug,
		show_overlay            = p.show_overlay,
		write_overlay           = p.write_overlay,
		print_stats             = p.stats,
		print_config            = p.print_config,
		list_config             = p.list_config_entries,
		force_distroot          = p.force_distroot,
		skip_manifest           = p.no_manifest,
		incremental             = p.incremental,
		immediate_ebuild_writes = p.immediate_ebuild_writes,
	)

	if given ( 'overlay' ):
		doconf ( p.overlay, 'OVERLAY.dir' )
		#extra ['write_overlay'] = True

	if given ( 'overlay_name' ):
		doconf ( p.overlay_name, 'OVERLAY.name' )

	if given ( 'field_definition' ):
		doconf ( p.field_definition, 'DESCRIPTION.field_definition_file' )

	if given ( 'repo_config' ):
		doconf ( p.repo_config, 'REPO.config_files' )

	if given ( 'distroot' ):
		doconf ( p.distroot, 'distfiles.root' )

	if given ( 'distdirs' ):
		if given ( 'distroot' ):
			raise Exception ( "--distdir and --disroot are mutually exclusive!" )

		doconf ( (), 'REPO.config_files' )
		extra ['distdirs'] = frozenset ( p.distdirs )
		extra ['nosync']   = True
		if 'create' in command_map:
			commands.append ( "create" )

	if given ( 'deprule_file' ):
		doconf ( p.deprule_file, 'DEPRES.SIMPLE_RULES.files' )

	if given ( 'manifest_implementation' ):
		doconf ( p.manifest_implementation, 'OVERLAY.manifest_implementation' )

	return ( commands, p.config, conf, extra )
# --- end of parse_argv (...) ---
