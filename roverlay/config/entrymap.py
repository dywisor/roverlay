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
CONFIG_ENTRY_MAP = dict (
	log_level = '',
	log_console = dict (
		value_type = 'yesno',
	),
	log_file = dict (
		# setting path to LOG.FILE.main to avoid collision with LOG.FILE.*
		path       = [ 'LOG', 'FILE', 'Main' ],
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
	overlay_category = dict (
		value_type = 'str',
	),
	overlay_eclass = dict (
		path       = [ 'OVERLAY', 'eclass_files' ],
		value_type = 'list:fs_abs:fs_file',
	),
	eclass = 'overlay_eclass',
	overlay_dir   = dict (
		value_type = 'fs_abs:fs_dir',
	),
	overlay_name = dict (
		value_type = 'str',
	),
	distfiles_dir = dict (
		value_type = 'fs_dir',
	),
	rsync_bwlimit = dict (
		path       = [ 'rsync_bwlimit' ],
		value_type = 'int',
	),
	ebuild_prog = dict (
		path       = [ 'TOOLS', 'ebuild_prog' ],
		value_type = 'fs_path',
	),
	simple_rules_files = dict (
		path       = [ 'DEPRES', 'SIMPLE_RULES', 'files' ],
		value_type = 'list:fs_abs',
	),
	simple_rules_file = 'simple_rules_files',
	repo_config = 'repo_config_files',
	repo_config_file = 'repo_config_files',
	repo_config_files = dict (
		path       = [ 'REPO', 'config_files' ],
		value_type = 'slist:fs_abs',
	),
)
