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

* value_type (string), you can specify:
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
LOG_LEVEL  = frozenset ((
   "DEBUG", "INFO", "WARN",
   "WARNING", "ERROR", "CRITICAL"
))

is_log_level = { 'choices' : LOG_LEVEL, 'flags' : CAPSLOCK }

only_vtype = lambda x : { 'value_type': x }

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
   ),
   log_file_unresolvable = dict (
      value_type  = fs_file,
      description = '''file where unresolved dependency strings
         will be written to
      '''
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
      description = '''overlay root directory where the
         ebuilds, profiles/ dir, etc. will be written to.
      '''
   ),

   overlay_additions_dir = dict (
      value_type  = 'fs_abs:fs_dir',
      description = 'directory containing ebuilds and ebuild patches',
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
         'portage',
#         'e',
#         'p',
      )),
   ),
   # ebuild is used to create Manifest files
   ebuild_prog = dict (
      path        = [ 'TOOLS', 'ebuild_exe' ],
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
      description = '''
         DISTDIR which is used for Manifest creation and can,
         depending on the DISTDIR strategy,
         serve as package mirror directory.
      '''
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

   # * alias
   backup_desc               = 'overlay_backup_desc',
   eclass                    = 'overlay_eclass',
   keep_nth_latest           = 'overlay_keep_nth_latest',
   manifest_implementation   = 'overlay_manifest_implementation',
   additions_dir             = 'overlay_additions_dir',
   distdir                   = 'overlay_distdir_root',
   distdir_strategy          = 'overlay_distdir_strategy',
   distdir_flat              = 'overlay_distdir_flat',

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
      description = '''distfiles root,
         repos will create their distdirs in this directory.
      ''',
   ),

   # the repo config file(s)
   repo_config_files = dict (
      path        = [ 'REPO', 'config_files' ],
      value_type  = fs_abslist,
      description = 'list of repo config files',
   ),

   # this option is used to limit bandwidth usage while running rsync
   rsync_bwlimit = dict (
      path        = [ 'rsync_bwlimit' ],
      value_type  = 'int',
      description = "max average rsync bandwidth usage (in kilobytes/second)"
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
   ),

   # * alias
   simple_rules_file = 'simple_rules_files',

   # --- dependency resolution


   # == description reader ==

   field_definition_file = dict (
      path        = [ 'DESCRIPTION', 'field_definition_file' ],
      value_type  = fs_file,
      description = "config file that controls DESCRIPTION file reading",
   ),

   # * for debugging
   # if set: write _all_ description files to dir/<package_filename>
   description_descfiles_dir = dict (
      path        = [ 'DESCRIPTION', 'descfiles_dir' ],
      value_type  = 'fs_abs:fs_dir',
      description = '''if set: write description files (read from tarballs)
         into this directory. Leave blank / comment out to disable.
      '''
   ),

   # * alias
   description_dir = 'description_descfiles_dir',
   field_definition = 'field_definition_file',

   # --- description reader

   # == package rules ==

   package_rule_files = dict (
      path        = [ 'PACKAGE_RULES', 'files' ],
      value_type  = fs_abslist,
      description = 'list of package rule files',
   ),

   # * alias
   package_rules = 'package_rule_files',

   # --- package rules

   # == other ==

   cachedir = dict (
      path        = [ 'CACHEDIR', 'root', ],
      value_type  = 'fs_dir',
      description = 'directory for cache data',
   ),

   tmpdir = dict (
      path        = [ 'TMPDIR', 'root', ],
      value_type  = 'fs_dir',
      description = 'directory for temporary data',
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
