# R overlay -- config package, entrymap
# -*- coding: utf-8 -*-
# Copyright (C) 2012 André Erdmann <dywi@mailerd.de>
# Distributed under the terms of the GNU General Public License;
# either version 2 of the License, or (at your option) any later version.

"""
config entry map

This module mainly consists of a map that defines all config entries.

Config entry map format:

<config_entry> = None|''|str|dict(...), where
* config_entry is the config entry name in lowercase (e.g. 'log_level')
* None   means that config_entry is known but ignored,
* str    means that config_entry is an alias for another config entry,
* ''     means that config_entry uses defaults,
* dict() means that config_entry has options that divert from the defaults.

known dict keys are 'path', 'description'/'desc' and 'value_type':
* path (string or list of strings) -- path of this entry in the config tree
* description (string)             -- describes the entry

* value_type can be any of:
-> list    -- value is a whitespace-separated list
-> int     -- integer
-> str     -- [explicit string conversion]
-> yesno   -- value must evaluate to 'yes' or 'no' (on,off,y,n,1,0...)
-> fs_path -- "~" will be expanded
-> fs_abs  -- fs_path and path will be converted into an absolute one
               (pwd + path)
-> fs_dir  -- fs_abs and value must be a dir if it exists
-> fs_file -- fs_abs and value must be a file if it exists
-> regex   -- value is a regex and will be compiled (re.compile(..))
-> a type (str,int,...)
-> a callable that accepts one arg and returns the converted value or None,
   where None means "not valid"

  Multiple types are generally not supported ('this is an int or a str'),
  but subtypes are ('list of yesno'), which can be specified by either
  using a list of types ['list', 'yesno'] or by separating the types
  with a colon 'list:yesno', which is parsed in a left-to-right order.
  Nested subtypes such as list:int:fs_file:list may lead to errors.

"""

__all__ = [ 'CONFIG_ENTRY_MAP', 'prune_description', ]

fs_file         = 'fs_file'
fs_abslist      = 'list:fs_abs'
yesno           = 'yesno'
list_of_choices = "list:str"

# often (>1) used entry dicts (it's ok to share a ref to those dicts
#  'cause CONFIG_ENTRY_MAP won't be modified)
is_fs_file = { 'value_type' : fs_file }
#is_str     = { 'value_type' : 'str' }
is_yesno   = { 'value_type' : 'yesno' }

CAPSLOCK   = ( 'CAPSLOCK', )
LOG_LEVEL  = ( "DEBUG", "INFO", "WARN", "WARNING", "ERROR", "CRITICAL" )

is_log_level = { 'choices' : LOG_LEVEL, 'flags' : CAPSLOCK }

only_vtype = lambda x : { 'value_type': x }

# mask for want_create_dir
WANT_PRIVATE = 1
WANT_FILEDIR = 2
WANT_USERDIR = 4

WANT_PUBLIC_DIR      = 0
WANT_PUBLIC_FILEDIR  = WANT_FILEDIR
WANT_PRIVATE_DIR     = WANT_PRIVATE
WANT_PRIVATE_FILEDIR = WANT_PRIVATE | WANT_FILEDIR


def _verify_distdir_strategy ( strategy, logger ):
   methods = set ( strategy )
   if not strategy:
      logger.error (
         'strategy must not be empty.'
      )
      return False
   elif len ( methods ) != len ( strategy ):
      logger.error (
         'specifying a method more than once makes no sense.'
      )
      return False
   elif 'tmpdir' in methods and len ( strategy ) > 1:
      logger.error (
         "the 'tmpdir' strategy does not accept any fallback methods!"
      )
      return False
   else:
      return True
# --- end of _verify_distdir_strategy (...) ---

CONFIG_ENTRY_MAP = dict (

   # == logging ==

   log_enabled = dict (
      value_type  = yesno,
      description = "enable/disable logging",
   ),
   log_level = dict (
      desc = "global log level, choices are {}.".format (
         ', '.join ( LOG_LEVEL )
      ),
      **is_log_level
   ),
   #log_format      = None, # there's no global log format
   log_date_format = dict (
      desc = "date format, example: '%F %H:%M:%S'.",
   ),

   # used in depres listener modules
   log_file_resolved = dict (
      value_type  = fs_file,
      description = '''NOT IN USE.
         file where resolved dep strings will be written to.
      ''',
      want_dir_create = WANT_PRIVATE_FILEDIR | WANT_USERDIR,
   ),
   log_file_unresolvable = dict (
      value_type  = fs_file,
      description = '''file where unresolved dependency strings
         will be written to
      ''',
      want_dir_create = WANT_PRIVATE_FILEDIR | WANT_USERDIR,
   ),

   # === logging to console ===

   log_console_enabled = dict (
      value_type  = yesno,
      description = "enable/disable logging to stdout/stderr",
   ),
   log_console         = 'log_console_enabled',

   log_console_level   = dict (
      desc = "log level for console logging.",
      **is_log_level
   ),
   log_level_console   = 'log_console_level',

   log_console_stream  = None, # option not configurable

   log_console_format  = dict (
      desc = '''console logging format,
         example: '%(levelname)-7s [%(name)s] %(message)s'
      ''',
   ),
   log_format_console  = 'log_console_format',

   # === logging to file ===

   log_file_enabled = dict (
      value_type  = yesno,
      description = "enable/disable logging to file",
   ),

   log_file = dict (
      # setting path to LOG.FILE.file to avoid collision with LOG.FILE.*
      path        = [ 'LOG', 'FILE', 'file' ],
      value_type  = fs_file,
      description = "log file to write",
      want_dir_create = WANT_PRIVATE_FILEDIR | WANT_USERDIR,
   ),

   log_file_level = dict (
      desc = "log level for file logging",
      **is_log_level
   ),
   log_level_file = 'log_file_level',

   log_file_rotate = dict (
      value_type  = yesno,
      description = "enable/disable log file rotating (per script run)",
   ),
   log_file_rotate_count = dict (
      path        = [ 'LOG', 'FILE', 'rotate_count' ],
      value_type  = 'int',
      description = "number of rotated log files to keep",
   ),

   log_file_format = dict (
      desc = '''file logging format,
         example: '%(asctime)s %(levelname)-8s %(name)-10s: %(message)s'
      '''
   ),
   log_format_file = 'log_file_format',

   log_file_buffered = dict (
      value_type  = yesno,
      description = "buffer log entries before writing them to file",
   ),

   log_file_buffer_count    = 'log_file_buffer_capacity',
   log_file_buffer_capacity = dict (
      path        = [ 'LOG', 'FILE', 'buffer_capacity' ],
      value_type  = 'int',
      description = "max number of log entries to buffer",
   ),


#   # === syslog ===
#
#   log_syslog_enabled = is_yesno,
#   log_syslog         = 'log_syslog_enabled',
#
#   log_syslog_level = is_log_level,
#   log_level_syslog = 'log_syslog_level',
#
   # --- logging


   # == overlay ==

   # COULDFIX key is not in use
   ebuild_header = dict (
      value_type  = fs_file,
      description = '''NOT IN USE.
         ebuild header file that will be included in every created ebuild.
      ''',
   ),

   overlay_backup_desc = dict (
      path        = [ 'OVERLAY', 'backup_desc' ],
      value_type  = yesno,
      description = 'back up files in/from profiles/desc',
   ),

   overlay_category = dict (
      desc = "overlay category to use for created ebuilds, e.g. 'sci-R'.",
   ),
   overlay_dir = dict (
      value_type = 'fs_abs:fs_dir',
      description = (
         'this is the directory of the overlay to be created/maintained'
      ),
      want_dir_create = WANT_PUBLIC_DIR | WANT_USERDIR,
   ),

   overlay_additions_dir = dict (
      path        = [ 'OVERLAY', 'additions_dir', ],
      value_type  = 'fs_abs:fs_dir',
      description = 'directory containing ebuilds and ebuild patches',
      # FIXME: WANT_USERDIR or not?
      want_dir_create = WANT_PRIVATE_DIR,
   ),

   overlay_eclass = dict (
      path        = [ 'OVERLAY', 'eclass_files' ],
      value_type  = fs_abslist,
      description = '''eclass files to import into the overlay.
         Automatically inherited in ebuilds.
      ''',
   ),

   overlay_name = dict (
      desc = "overlay name, e.g. 'R-Overlay'.",
   ),

   overlay_manifest_implementation = dict (
      desc    = "manifest implementation to be used",
      path    = [ 'OVERLAY', 'manifest_implementation' ],
      choices = frozenset ((
         'none',
         'default',
         'ebuild',
         'next',
#         'e',
      )),
   ),
   # ebuild is used to create Manifest files
   ebuild_prog = dict (
      path        = [ 'TOOLS', 'EBUILD', 'exe' ],
      value_type  = 'fs_path',
      description = "name of/path to the ebuild executable",
   ),


   overlay_keep_nth_latest = dict (
      path        = [ 'OVERLAY', 'keep_nth_latest' ],
      value_type  = 'int',
      description = 'number of ebuilds per R package to keep (if > 0)',
   ),

   overlay_distdir_root = dict (
      value_type  = 'fs_dir',
      description = (
         'this is the directory where hard/symbolic links '
         'to all package files will be created '
         '(during Manifest file creation)'
      ),
      want_dir_create = WANT_PUBLIC_DIR | WANT_USERDIR,
   ),

   overlay_distdir_strategy = dict (
      description = "list of DISTDIR creation methods",
      value_type  = list_of_choices,
      choices     = frozenset ((
         "symlink",
         "hardlink",
         "copy",
         "tmpdir",
      )),
      f_verify    = _verify_distdir_strategy,
   ),

   overlay_distdir_flat = dict (
      description = (
         "whether to use per-package distdirs (False) or not (True)"
      ),
      value_type  = yesno,
   ),

   overlay_distdir_verify = dict (
      description = 'check integrity of distdir files on startup',
      value_type  = yesno,
   ),

   overlay_distmap_compression = dict (
      description = 'distmap compression format (none, bzip2 or gzip)',
      choices     = frozenset ({
         'none', 'default', 'bz2', 'bzip2', 'gz', 'gzip'
      }),
   ),

   overlay_distmap_file = dict (
      path        = [ 'OVERLAY', 'DISTMAP', 'dbfile', ],
      value_type  = 'fs_file',
      description = 'distmap file',
      want_dir_create = WANT_PRIVATE_FILEDIR | WANT_USERDIR,
   ),

   overlay_masters = dict (
      path        = [ 'OVERLAY', 'masters', ],
      value_type  = 'list:str',
      description = 'masters attribute for metadata/layout.conf',
   ),

   # * alias
   backup_desc               = 'overlay_backup_desc',
   eclass                    = 'overlay_eclass',
   keep_nth_latest           = 'overlay_keep_nth_latest',
   manifest_implementation   = 'overlay_manifest_implementation',
   additions_dir             = 'overlay_additions_dir',
   distdir                   = 'overlay_distdir_root',
   distdir_strategy          = 'overlay_distdir_strategy',
   distdir_flat              = 'overlay_distdir_flat',
   distdir_verify            = 'overlay_distdir_verify',
   distmap_compression       = 'overlay_distmap_compression',
   distmap_file              = 'overlay_distmap_file',

   # --- overlay

   # == ebuild ==

   ebuild_eapi = None,
#   ebuild_eapi = dict (
#      description = "EAPI of the created ebuilds",
#      value_type  = str,
#   ),

   ebuild_use_expand_desc = dict (
      path        = [ 'EBUILD', 'USE_EXPAND', 'desc_file', ],
      description = "USE_EXPAND flag description file",
      value_type  = 'fs_file',
      want_dir_create = WANT_PRIVATE_FILEDIR,
   ),

   ebuild_use_expand_name = dict (
      path        = [ 'EBUILD', 'USE_EXPAND', 'name', ],
      description = (
         'name of the USE_EXPAND variable for suggested dependencies'
      )
   ),

   ebuild_use_expand_rename = dict (
      path        = [ 'EBUILD', 'USE_EXPAND', 'rename_file', ],
      description = 'file for renaming USE_EXPAND flags',
      value_type  = 'fs_file',
      want_dir_create = WANT_PRIVATE_FILEDIR,
   ),

   # * alias
   #eapi              = 'ebuild_eapi',
   use_expand_desc   = 'ebuild_use_expand_desc',
   use_expand_name   = 'ebuild_use_expand_name',
   use_expand_rename = 'ebuild_use_expand_rename',

   # --- ebuild


   # == remote ==

   # the distfiles root directory
   #  this is where repos create their own DISTDIR as sub directory unless
   #  they specify another location
   distfiles_root = dict (
      value_type  = 'fs_dir',
      description = (
         'this is the directory where per-repo package directories '
         'will be created'
      ),
      want_dir_create = WANT_PRIVATE_DIR | WANT_USERDIR,
   ),

   # the repo config file(s)
   repo_config_files = dict (
      path        = [ 'REPO', 'config_files' ],
      value_type  = fs_abslist,
      description = 'list of repo config files',
      want_dir_create = WANT_PRIVATE_FILEDIR,
   ),

   # this option is used to limit bandwidth usage while running rsync
   rsync_bwlimit = dict (
      path        = [ 'REPO', 'rsync_bwlimit' ],
      value_type  = 'int',
      description = "max average rsync bandwidth usage (in kilobytes/second)"
   ),

   websync_timeout = dict (
      path        = [ 'REPO', 'websync_timeout' ],
      value_type  = 'int',
      description = "timeout for websync repo connections (in seconds)"
   ),

   # * alias
   distfiles        = 'distfiles_root',
   repo_config      = 'repo_config_files',
   repo_config_file = 'repo_config_files',

   # --- remote


   # == dependency resolution ==

   # the list of simple dep rule files
   simple_rules_files = dict (
      path        = [ 'DEPRES', 'SIMPLE_RULES', 'files' ],
      value_type  = fs_abslist,
      description = "list of dependency rule files",
      want_dir_create = WANT_PRIVATE_FILEDIR,
   ),

   # * alias
   simple_rules_file = 'simple_rules_files',

   # --- dependency resolution


   # == description reader ==

   field_definition_file = dict (
      path        = [ 'DESCRIPTION', 'field_definition_file' ],
      value_type  = fs_file,
      description = "config file that controls DESCRIPTION file reading",
      want_dir_create = WANT_PRIVATE_FILEDIR,
   ),

   # * for debugging
   # if set: write _all_ description files to dir/<package_filename>
   description_descfiles_dir = dict (
      path        = [ 'DESCRIPTION', 'descfiles_dir' ],
      value_type  = 'fs_abs:fs_dir',
      description = '''if set: write description files (read from tarballs)
         into this directory. Leave blank / comment out to disable.
      ''',
      want_dir_create = WANT_PRIVATE_FILEDIR | WANT_USERDIR,
   ),

   # * alias
   description_dir = 'description_descfiles_dir',
   field_definition = 'field_definition_file',

   # --- description reader

   # == package rules ==

   package_rule_files = dict (
      path        = [ 'PACKAGE_RULES', 'files' ],
      value_type  = fs_abslist,
      description = 'list of package rule files/dirs',
      want_dir_create = WANT_PRIVATE_FILEDIR,
   ),

   # * alias
   package_rules = 'package_rule_files',

   # --- package rules

   # == hooks / scripts ==

   filter_shell_env = dict (
      path        = [ 'SHELL_ENV', 'filter_env', ],
      value_type  = yesno,
      description = 'filter shell env',
   ),

   shell = dict (
      path        = [ 'SHELL_ENV', 'shell', ],
      description = "default command interpreter (for roverlay-sh etc.)",
   ),

   event_hook = dict (
      path        = [ 'EVENT_HOOK', 'exe', ],
      value_type  = 'fs_file',
      description = 'script that is run on certain events, e.g. overlay_success',
   ),

   event_hook_rc = dict (
      path        = [ 'EVENT_HOOK', 'config_file', ],
      value_type  = 'fs_abs',
      description = 'hook (shell) config file',
   ),

   event_hook_restrict = dict (
      path        = [ 'EVENT_HOOK', 'restrict', ],
      value_type  = 'list:str',
      description = 'mask for running hooks',
   ),


   # * alias
   hook          = 'event_hook',
   hook_rc       = 'event_hook_rc',
   hook_restrict = 'event_hook_restrict',


   # == license map ==

   license_map = dict (
      path        = [ 'LICENSEMAP', 'file', ],
      value_type  = 'fs_file',
      description = 'dictionary file for translating license strings',
   ),

   use_portage_licenses = dict (
      path        = [ 'LICENSEMAP', 'use_portdir', ],
      value_type  = 'yesno',
      description = 'try to read licenses from PORTDIR/licenses',
   ),

   # hidden option (using CACHEDIR.root + "/licenses" as licenses file)
   licenses_file = None,
#   licenses_file = dict (
#      path        = [ 'LICENSEMAP', 'licenses_file', ],
#      value_type  = 'fs_file',
#      description = (
#         'licenses file (used as fallback if PORTDIR not available)'
#      ),
#   ),

   create_licenses_file = dict (
      path        = [ 'LICENSEMAP', 'create_licenses_file', ],
      value_type  = 'yesno',
      description = 'create a licenses file after reading portage licenses',
   ),

   # hidden option (always using bzip2)
   licenses_file_compression = None,


   # * alias
   license_file             = 'licenses_file',
   create_license_file      = 'create_licenses_file',
   license_file_compression = 'licenses_file_compression',

   # --- license map

   # == stats / status report generation ==

   template_root = dict (
      path        = [ 'STATS', 'TEMPLATE', 'root', ],
      value_type  = 'list:fs_dir',
      description = 'directories with templates for status reports',
   ),

   template_module_dir = dict (
      path        = [ 'STATS', 'TEMPLATE', 'module_dir', ],
      value_type  = 'fs_dir',
      description = 'directory for caching templates',
   ),

   stats_db = dict (
      path        = [ 'STATS', 'dbfile', ],
      value_type  = 'fs_file',
      description = 'stats database file',
   ),

   stats_interval = dict (
      path        = [ 'RRD_DB', 'step', ],
      value_type  = 'int',
      description = (
         'database update interval (only used for creating new database files)'
      ),
   ),

   # --- stats / status report generation

   # == other ==

   cachedir = dict (
      path        = [ 'CACHEDIR', 'root', ],
      value_type  = 'fs_dir',
      description = 'directory for cache data',
      want_dir_create = WANT_PRIVATE_DIR | WANT_USERDIR,
   ),

   nosync = dict (
      value_type  = yesno,
      description = 'forbid/allow syncing with remotes',
   ),

   portdir = dict (
      value_type  = 'fs_dir',
      description = 'path to the portage directory (usually /usr/portage)',
   ),

   # --- other

)

del fs_file, fs_abslist, is_fs_file, is_yesno, is_log_level, \
   CAPSLOCK, LOG_LEVEL, only_vtype

def prune_description():
   """Removes the description strings from all config entries."""
   for entry in CONFIG_ENTRY_MAP.values():
      if isinstance ( entry, dict ):

         if 'description' in entry:
            del entry ['description']
         elif 'desc' in entry:
            del entry ['desc']
