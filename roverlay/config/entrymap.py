# <header!!>

# TODO/FIXME comments

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
# ** str     -- [explicit string conversion]
# ** yesno   -- value must evaluate to 'yes' or 'no' (on,off,y,n,1,0...)
# ** fs_path -- ~ will be expanded
# ** fs_abs  -- fs_path and path will be converted into an absolute one
#                (pwd + path)
# ** fs_dir  -- fs_abs and value must be a dir if it exists
# ** fs_file -- fs_abs and value must be a file if it exists
# TODO** fs_prog -- fs_file (and fs_path) and value must be executable (TODO)
# ** regex   -- value is a regex and will be compiled (re.compile(..))
#
#   multiple types are generally not supported ('this is an int or a str'),
#   but subtypes are ('list of yesno'), which can be specified by either
#   using a list of types ['list', 'yesno'] or by separating the types
#   with a colon 'list:yesno', which is parsed in a left-to-right order.
#   Nested subtypes such as list:slist:int:fs_file:list may lead to errors.
#

fs_file    = 'fs_file'
fs_abslist = 'slist:fs_abs'

# often (>1) used entry dicts (it's ok to share a ref to those dicts
#  'cause CONFIG_ENTRY_MAP won't be modified)
is_fs_file = { 'value_type' : fs_file }
is_str     = { 'value_type' : 'str' }

only_vtype = lambda x : { 'value_type': x }

CONFIG_ENTRY_MAP = dict (

	# == logging ==

	log_level   = '',
	log_console = only_vtype ( 'yesno' ),
	log_file = dict (
		# setting path to LOG.FILE.main to avoid collision with LOG.FILE.*
		path       = [ 'LOG', 'FILE', 'main' ],
		value_type = fs_file,
	),
	log_file_resolved     = is_fs_file,
	log_file_unresolvable = is_fs_file,

	# --- logging


	# == overlay ==

	# FIXME key is not in use
	ebuild_header    = is_fs_file,

	overlay_category = is_str, # e.g. 'sci-R'
	overlay_dir      = only_vtype ( 'fs_abs:fs_dir' ),

	overlay_eclass = dict (
		path       = [ 'OVERLAY', 'eclass_files' ],
		value_type = fs_abslist,
	),

	overlay_name = is_str,

	# ebuild is used to create Manifest files
	ebuild_prog = dict (
		path       = [ 'TOOLS', 'ebuild_prog' ],
		value_type = 'fs_path',
	),

	# * alias
	eclass = 'overlay_eclass',

	# --- overlay


	# == remote ==

	# the distfiles root directory
	#  this is where repos create their own DISTDIR as sub directory unless
	#  they specify another location
	distfiles_root = only_vtype ( 'fs_dir' ),

	# the repo config file(s)
	repo_config_files = dict (
		path       = [ 'REPO', 'config_files' ],
		value_type = fs_abslist,
	),

	# this option is used to limit bandwidth usage while running rsync
	rsync_bwlimit = dict (
		path       = [ 'rsync_bwlimit' ],
		value_type = 'int',
	),

	# * alias
	distfiles        = 'distfiles_root',
	distdir          = 'distfiles_root',
	repo_config      = 'repo_config_files',
	repo_config_file = 'repo_config_files',

	# --- remote


	# == dependency resolution ==

	# the list of simple dep rule files
	simple_rules_files = dict (
		path       = [ 'DEPRES', 'SIMPLE_RULES', 'files' ],
		value_type = fs_abslist,
	),

	# * alias
	simple_rules_file = 'simple_rules_files',

	# --- dependency resolution

	# == description reader ==

	# * for debugging
	# if set: write _all_ description files to dir/<package_filename>
	description_descfiles_dir = dict (
		path       = [ 'DESCRIPTION', 'descfiles_dir' ],
		value_type = 'fs_abs:fs_dir',
	),

	# * alias
	description_dir = 'description_descfiles_dir',

)
