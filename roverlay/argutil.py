
import os.path
import argparse
import roverlay

def get_parser ( CMD_DESC, DEFAULT_CONFIG ):

	def is_fs_file ( value ):
		f = os.path.abspath ( value )
		if not os.path.isfile ( f ):
			raise argparse.ArgumentTypeError (
				"%r is not a file." % value
			)
		return f

	def is_fs_dir ( value ):
		d = os.path.abspath ( value )
		if not os.path.isdir ( d ):
			raise argparse.ArgumentTypeError (
				"%r is not a directory." % value
			)
		return d

	def couldbe_fs_dir ( value ):
		d = os.path.abspath ( value )
		if os.path.exists ( d ) and not os.path.isdir ( d ):
			raise argparse.ArgumentTypeError (
				"%r cannot be a directory." % value
			)
		return d

	parser = argparse.ArgumentParser (
		description='\n'.join ((
			roverlay.description_str, roverlay.license_str,
		)),
		epilog = 'Known commands:\n' + '\n'.join (
			( ( '* ' + c ).ljust(17) + ' - ' + d for (c,d) in CMD_DESC.items() )
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
		'-V', '--version', action='version', version=roverlay.version_str
	)

	arg (
		'commands',
		# fixme: CMD_DESC is "unknown", but default is set to a specific command
		default='create',
		help="action to perform. choices are " + ', '.join (CMD_DESC.keys()) + \
			". defaults to %(default)s.",
		nargs="*",
		choices=CMD_DESC.keys(),
		metavar="command"
	)

	arg (
		'-c', '--config',
		default=DEFAULT_CONFIG,
		help="config file",
		**fs_file
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
		**fs_file
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
		'--show',
		help="print ebuilds and metadata to console",
		**opt_in
	)

	arg (
		'--write',
		help="write overlay to filesystem",
		# !! change to opt_out (FIXME)
		**opt_in
	)


	arg (
		'--nosync', '--no-sync',
		help="disable syncing with remotes (offline mode). TODO",
		**opt_in
	)
	arg (
		'--force-distroot',
		help="always use <DISTROOT>/<repo name> as repo distdir. TODO.",
		**opt_in
	)

	arg (
		'--debug',
		help='''
			Turn on debugging. This produces a lot of messages.
			(TODO: always on).
		''',
		**opt_out
	)

	return parser
# --- end of get_parser (...) ---

def parse_argv ( *args, **kw ):
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


	p = get_parser ( *args, **kw ).parse_args()

	given = lambda kw : hasattr ( p, kw )


	conf  = dict()
	extra = dict (
		nosync         = p.nosync,
		show           = p.show,
		write          = p.write,
		debug          = p.debug,
		force_distroot = p.force_distroot,
	)

	if given ( 'field_definition' ):
		doconf ( p.field_definition, 'DESCRIPTION.field_definition_file' )

	if given ( 'repo_config' ):
		doconf ( p.repo_config, 'REPO.config_files' )

	if given ( 'distroot' ):
		doconf ( p.distroot, 'distfiles.root' )

	if given ( 'distdir' ):
		doconf ( (), 'REPO.config_files' )
		extra ['distdir'] = p.distdir

	if given ( 'deprule_file' ):
		doconf ( p.deprule_file, 'DEPRES.SIMPLE_RULES.files' )


	return (
		( p.commands, ) if isinstance ( p.commands, str ) else p.commands,
		p.config, conf, extra
	)
# --- end of parse_argv (...) ---
