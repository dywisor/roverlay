# R overlay -- roverlay package, arg parser
# -*- coding: utf-8 -*-
# Copyright (C) 2012, 2013 André Erdmann <dywi@mailerd.de>
# Distributed under the terms of the GNU General Public License;
# either version 2 of the License, or (at your option) any later version.

import os
import argparse
import collections

import roverlay.core
import roverlay.argutil
import roverlay.util.objects

# lazy import
from roverlay.argutil import \
   couldbe_fs_dir, couldbe_fs_file, couldbe_stdout_or_file, \
   get_gid, is_gid, get_uid, is_uid, \
   is_fs_dir, is_fs_dir_or_void, is_fs_file, \
   is_fs_file_or_dir, is_fs_file_or_void, \
   ArgumentParserProxy


class RoverlayArgumentParserBase ( roverlay.argutil.ArgumentParserProxy ):

   DESCRIPTION_TEMPLATE = None

   def __init__ (
      self, defaults=None, description=True, formatter_class=True,
      format_description=False, **kwargs
   ):
      if description is True:
         if self.DESCRIPTION_TEMPLATE is None:
            desc = (
               roverlay.core.description_str + '\n'
               + roverlay.core.license_str
            )
         else:
            desc = self.format_description()
      elif description:
         if format_description:
            desc = self.format_description ( description )
         else:
            desc = description
      else:
         desc = None

      super ( RoverlayArgumentParserBase, self ).__init__ (
         defaults        = defaults,
         description     = desc,
         formatter_class = (
            argparse.RawDescriptionHelpFormatter
            if formatter_class is True else formatter_class
         ),
         **kwargs
      )


      self.extra_conf = None
   # --- end of __init__ (...) ---

   def format_description ( self, desc=None ):
      return ( self.DESCRIPTION_TEMPLATE if desc is None else desc ).format (
         version=roverlay.core.version,
         license=roverlay.core.license_str,
      )
   # --- end of format_description (...) ---

   def format_command_map ( self, command_map ):
      return (
         "\nKnown commands:\n" + '\n'.join (
            # '* <space> <command> - <command description>'
            '* {cmd} - {desc}'.format (
               cmd=cmd.ljust ( 15 ), desc=desc
            ) for cmd, desc in command_map.items()
         )
      )
   # --- end of format_command_map (...) ---

   def do_extraconf ( self, value, path ):
      pos = self.extra_conf
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

      return pos
   # --- end of do_extraconf (...) ---

   def do_extraconf_simple ( self, attr_name, path ):
      if attr_name in self.parsed:
         self.do_extraconf ( self.parsed[attr_name], path )
         return True
      else:
         return False
   # --- end of do_extraconf_simple (...) ---

   def parse ( self, *args, **kwargs ):
      self.parse_args ( *args, **kwargs )
      parsed          = vars ( self.parsed )
      self.parsed     = parsed
      self.extra_conf = dict()

      conf_ifdef = self.do_extraconf_simple

      # config
      conf_ifdef ( 'field_definition', 'DESCRIPTION.field_definition_file' )
      conf_ifdef ( 'repo_config', 'REPO.config_files' )
      conf_ifdef ( 'deprule_file', 'DEPRES.SIMPLE_RULES.files' )
      conf_ifdef ( 'package_rules', 'PACKAGE_RULES.files' )


      # overlay
      conf_ifdef ( 'overlay_dir', 'OVERLAY.dir' )
      conf_ifdef ( 'overlay_name', 'OVERLAY.name' )
      conf_ifdef ( 'additions_dir', 'OVERLAY.additions_dir' )
      if 'write_overlay' in parsed:
         self.do_extraconf (
            not ( parsed ['write_overlay'] ), 'write_disabled'
         )


      # remote_minimal
      if 'sync' in parsed:
         self.do_extraconf ( not ( parsed ['sync'] ), 'nosync' )


      # remote
      if conf_ifdef ( 'distroot', 'DISTFILES.root' ):
         if 'local_distdirs' in parsed:
            raise Exception (
               "--force-distroot and --distroot are mutually exclusive."
            )
      elif 'local_distdirs' in parsed:
         parsed ['local_distdirs'] = frozenset ( parsed ['local_distdirs'] )

         # --from implies --no-sync and disables all repo config files
         self.do_extraconf ( (), 'REPO.config_files' )
         self.do_extraconf ( True, 'nosync' )

      conf_ifdef ( 'sync_in_hooks', 'sync_in_hooks' )

      # overlay creation
      conf_ifdef ( 'distmap_verify', 'OVERLAY.DISTDIR.verify' )
      conf_ifdef (
         'manifest_implementation', 'OVERLAY.manifest_implementation'
      )

      if (
         parsed.get ( 'fixup_category_move' ) and
         parsed.get ( 'fixup_category_move_reverse' )
      ) or (
         not parsed.get ( 'incremental', True ) and (
            parsed.get ( 'fixup_category_move' ) or
            parsed.get ( 'fixup_category_move_reverse' )
         )
      ):
         raise Exception (
            'mutually exclusive: --fixup-category-move{,-reverse}, '
            '--no-incremental'
         )


      if hasattr ( self.__class__, 'PARSE_TARGETS' ):
         for attr in self.__class__.PARSE_TARGETS:
            getattr ( self, 'parse_' + attr )()
   # --- end of parse (...) ---

   def setup ( self ):
      if hasattr ( self.__class__, 'SETUP_TARGETS' ):
         for attr in self.__class__.SETUP_TARGETS:
            getattr ( self, 'setup_' + attr )()
      else:
         raise roverlay.util.objects.AbstractMethodError ( self, 'setup' )
   # --- end of setup (...) ---

   def setup_version ( self ):
      self.arg (
         '-V', '--version', action='version',
         version=self.defaults.get ( "version", roverlay.core.version )
      )
   # --- end of setup_version (...) ---

   def setup_config_minimal ( self ):
      config_arg = self.add_argument_group (
         'config', title='config file options'
      )

      config_arg (
         '-c', '--config', dest='config_file', help='config_file',
         type=is_fs_file_or_void,
         flags=self.ARG_WITH_DEFAULT|self.ARG_META_FILE,
      )

      return config_arg
   # --- end of setup_config_minimal (...) ---

   def parse_config ( self ):
      if not self.parsed ['config_file']:
         roverlay.core.die (
            "No config file found.\n", roverlay.core.DIE.CONFIG
         )
   # --- end of parse_config (...) ---

   def setup_config ( self ):
      config_arg = self.setup_config_minimal()

      config_arg (
         '-F', '--field-definition', '--fdef', dest='field_definition',
         default=argparse.SUPPRESS, type=is_fs_file,
         flags=self.ARG_ADD_DEFAULT|self.ARG_META_FILE,
         help="field definition file",
      )

      config_arg (
         '-R', '--repo-config', dest='repo_config',
         default=argparse.SUPPRESS, type=is_fs_file, action='append',
         flags=self.ARG_ADD_DEFAULT|self.ARG_META_FILE,
         help="repo config file(s)",
      )

      config_arg (
         '-D', '--deprule-file', dest='deprule_file',
         default=argparse.SUPPRESS, type=is_fs_file_or_dir,
         action='append',
         flags=self.ARG_ADD_DEFAULT|self.ARG_META_FILEDIR,
         help="dependency rule file(s)",
      )

      config_arg (
         '-P', '--package-rules', dest='package_rules',
         default=argparse.SUPPRESS, type=is_fs_file_or_dir,
         action='append',
         flags=self.ARG_ADD_DEFAULT|self.ARG_META_FILEDIR,
         help="package rule file(s)",
      )

      return config_arg
   # --- end of setup_config (...) ---

   def setup_overlay_minimal ( self ):
      arg = self.add_argument_group (
         'overlay', title='overlay options'
      )
      ## !!! INCREMENTAL_MUTEX

      arg (
         '-O', '--overlay', dest='overlay_dir',
         default=argparse.SUPPRESS, type=couldbe_fs_dir,
         flags=self.ARG_ADD_DEFAULT|self.ARG_META_DIR,
         help="overlay directory (implies --write-overlay)",
      )

      arg (
         '-N', '--overlay-name', dest='overlay_name',
         default=argparse.SUPPRESS, metavar='<name>',
         flags=self.ARG_ADD_DEFAULT,
         help="overlay name",
      )

      arg (
         '-A', '--additions-dir', dest='additions_dir',
         default=argparse.SUPPRESS,
         flags=self.ARG_ADD_DEFAULT|self.ARG_META_DIR,
         type=is_fs_dir_or_void,
         help="directory containing patches and hand-written ebuilds",
      )

      arg (
         '--write-overlay', '--write', dest='write_overlay',
         default=True, flags=self.ARG_WITH_DEFAULT|self.ARG_OPT_IN,
         help="allow overlay writing",
      )
      arg (
         '--no-write-overlay', '--no-write', dest='write_overlay',
         flags=self.ARG_SHARED_INVERSE|self.ARG_OPT_OUT,
         help="forbid overlay writing",
      )

      arg (
         '--show-overlay', '--show', dest='show_overlay',
         flags=self.ARG_WITH_DEFAULT|self.ARG_OPT_IN,
         help="print the overlay to stdout",
      )
      arg (
         '--no-show-overlay', '--no-show', dest='show_overlay',
         flags=self.ARG_SHARED_INVERSE|self.ARG_OPT_OUT,
         help="don\'t print the overlay",
      )


      return arg
   # --- end of setup_overlay_minimal (...) ---

   def setup_overlay ( self ):
      arg = self.setup_overlay_minimal()

      return arg
   # --- end of setup_overlay (...) ---

   def setup_overlay_creation ( self ):
      arg = self.add_argument_group (
         "overlay_creation", title='overlay creation options',
      )

      arg (
         '--incremental', dest='incremental', default=True,
         flags=self.ARG_WITH_DEFAULT|self.ARG_OPT_IN,
         help="scan for existing and do not recreate them",
      )
      arg (
         '--no-incremental', dest='incremental',
         flags=self.ARG_SHARED_INVERSE|self.ARG_OPT_OUT,
         help="do not scan for existing ebuilds (recreate all)",
      )

      arg (
         '--fixup-category-move', dest='fixup_category_move',
         flags=self.ARG_WITH_DEFAULT|self.ARG_OPT_IN,
         help=(
            'remove packages from the default category if '
            'they exist in another one'
         ),
      )
      arg (
         '--fixup-category-move-reverse', dest='fixup_category_move_reverse',
         flags=self.ARG_WITH_DEFAULT|self.ARG_OPT_IN,
         help=(
            'remove packages from other categories if they exist in the '
            'default one'
         ),
      )

      arg (
         '--distmap-verify', dest='distmap_verify',
         default=argparse.SUPPRESS,
         flags=self.ARG_WITH_DEFAULT|self.ARG_OPT_IN,
         help=(
            'check integrity of files in the mirror directory and '
            'update the distmap file'
         ),
      )

      arg (
         '--revbump', dest='revbump', default=True,
         flags=self.ARG_WITH_DEFAULT|self.ARG_OPT_IN,
         help="revbump on package file checksum change",
      )
      arg (
         '--no-revbump', dest='revbump',
         flags=self.ARG_SHARED_INVERSE|self.ARG_OPT_OUT,
         help="disable revbump feature (saves time)",
      )

      arg (
         '--immediate-ebuild-writes', dest='immediate_ebuild_writes',
         flags=self.ARG_WITH_DEFAULT|self.ARG_OPT_IN,
         help=(
            'write ebuilds as soon as they\'re ready, which saves '
            'memory but costs more time'
         ),
      )

      arg (
         '--manifest', dest='manifest', default=True,
         flags=self.ARG_WITH_DEFAULT|self.ARG_OPT_IN,
         help="enable Manifest creation",
      )
      arg (
         '--no-manifest', dest='manifest',
         flags=self.ARG_SHARED_INVERSE|self.ARG_OPT_OUT,
         help="skip Manifest creation (results in useless overlay)",
      )

      arg (
         '-M', '--manifest-implementation', dest='manifest_implementation',
         choices=( 'default', 'next', 'ebuild', 'e' ),
         default=argparse.SUPPRESS, flags=self.ARG_WITH_DEFAULT,
         help="choose how Manifest files are created (ebuild(1) or internal)",
      )
   # --- end of setup_overlay_creation (...) ---

   def setup_remote_minimal ( self ):
      arg = self.add_argument_group ( "remote", title="sync options" )

      arg (
         '--strict-sync', dest='strict_sync',
         flags=self.ARG_WITH_DEFAULT|self.ARG_OPT_IN,
         help="exit if any repository cannot be used",
      )

      arg (
         '--sync', dest='sync', default=argparse.SUPPRESS,
         flags=self.ARG_WITH_DEFAULT|self.ARG_OPT_IN,
         help="allow syncing with remotes",
      )
      arg (
         '--nosync', '--no-sync', dest='sync',
         flags=self.ARG_SHARED_INVERSE|self.ARG_OPT_OUT,
         help="forbid syncing with remotes (offline mode)",
      )

      return arg
   # --- end of setup_remote_minimal (...) ---

   def setup_remote ( self ):
      arg = self.setup_remote_minimal()

      arg (
         '--sync-imports', dest='sync_imported', default=argparse.SUPPRESS,
         flags=self.ARG_WITH_DEFAULT|self.ARG_OPT_IN,
         help=(
            'allow fetching of source files for imported ebuilds even if '
            'sync is forbidden'
         ),
      )

      arg (
         '--sync-in-hooks', dest='sync_in_hooks', default=argparse.SUPPRESS,
         flags=self.ARG_WITH_DEFAULT|self.ARG_OPT_IN,
         help='allow syncing in hooks even if sync is forbidden',
      )

      arg (
         '--distroot', dest='distroot', default=argparse.SUPPRESS,
         flags=self.ARG_WITH_DEFAULT|self.ARG_META_DIR,
         type=couldbe_fs_dir,
         help=(
            'use %(metavar)s as distdir root directory for repositories '
            'that don\'t declare their own package directory.'
         ),
      )

      arg (
         '--force-distroot', dest='force_distroot',
         flags=self.ARG_WITH_DEFAULT|self.ARG_OPT_IN,
         help='always use package directories in --distroot',
      )

      arg (
         '--local-distdir', '--from', dest='local_distdirs',
         action='append', default=argparse.SUPPRESS,
         flags=self.ARG_META_DIR, type=is_fs_dir,
         help=(
            'ignore all repos and use packages from %(metavar)s for '
            'ebuild creation. only useful for testing since SRC_URI '
            'will be invalid. [disabled]'
         ),
      )

      return arg
   # --- end of setup_remote (...) ---

   def setup_misc_minimal ( self ):
      arg = self.add_argument_group ( "misc", title="misc options" )

      arg (
         '--strict', dest='strict',
         flags=self.ARG_WITH_DEFAULT|self.ARG_OPT_IN,
         help="enable all --strict options",
      )

      arg (
         '--stats', dest='print_stats', default=True,
         flags=self.ARG_WITH_DEFAULT|self.ARG_OPT_IN,
         help="print some stats",
      )
      arg (
         '--no-stats', dest='print_stats',
         flags=self.ARG_SHARED_INVERSE|self.ARG_OPT_OUT,
         help="don\'t print stats"
      )

      arg (
         '--dump-stats', dest='dump_stats',
         flags=self.ARG_WITH_DEFAULT|self.ARG_OPT_IN,
         help='print all stats to stdout at exit (raw format)',
      )


      return arg
   # --- end of setup_misc_minimal (...) ---

   def setup_misc ( self ):
      return self.setup_misc_minimal()
   # --- end of setup_misc (...) ---


# --- end of RoverlayArgumentParserBase ---

class RoverlayArgumentParser ( RoverlayArgumentParserBase ):

   COMMAND_DESCRIPTION = None
   DEFAULT_COMMAND     = None

   def __init__ ( self, default_command=None, **kwargs ):
      super ( RoverlayArgumentParser, self ).__init__ ( **kwargs )
      self.default_command = (
         self.DEFAULT_COMMAND if default_command is None else default_command
      )
      self.command = None

      if self.default_command:
         assert self.default_command in self.COMMAND_DESCRIPTION
   # --- end of __init__ (...) ---

   def setup_actions ( self ):
      arg = self.add_argument_group (
         "actions", title="actions",
         description=self.format_command_map ( self.COMMAND_DESCRIPTION ),
      )

      arg (
         'command', default=self.default_command, metavar='<action>',
         nargs="?", choices=self.COMMAND_DESCRIPTION.keys(),
         flags=self.ARG_HELP_DEFAULT,
         help="action to perform"
      )

      return arg
   # --- end of setup_actions (...) ---

   def parse_actions ( self ):
      self.command = self.parsed ['command']
   # --- end of parse_actions (...) ---

# --- end of RoverlayArgumentParser ---

class RoverlayStatusArgumentParser ( RoverlayArgumentParser ):

   DESCRIPTION_TEMPLATE = "roverlay status tool {version}\n{license}"

   SETUP_TARGETS = (
      'version',
      'output_options', 'script_mode', 'config_minimal',
      'actions',
   )
   PARSE_TARGETS = ( 'config', 'actions', 'extra', )

   COMMAND_DESCRIPTION = {
      'status': 'report overlay status',
   }
   DEFAULT_COMMAND = 'status'

   MODES = ( 'cli', 'cgi', 'html', )
   DEFAULT_MODE = 'cli'

   def setup_script_mode ( self ):
      arg = self.add_argument_group (
         "script_mode", title="script mode",
      )

      arg (
         '-m', '--mode', dest='script_mode',
         default=self.DEFAULT_MODE, metavar='<mode>',
         flags=self.ARG_WITH_DEFAULT, choices=self.MODES,
         help='set script mode (%(choices)s)',
      )

      for script_mode in self.MODES:
         arg (
            '--' + script_mode, dest='script_mode',
            flags=self.ARG_SHARED, action='store_const', const=script_mode,
            help='set script mode to {!r}'.format ( script_mode ),
         )

      return arg
   # --- end of setup_script_mode (...) ---

   def setup_output_options ( self ):
      arg = self.add_argument_group (
         'output_options', title='output options',
      )

      arg (
         '-O', '--output', dest='outfile', default='-',
         flags=self.ARG_WITH_DEFAULT|self.ARG_META_FILE,
         type=couldbe_stdout_or_file,
         help='output file (or stdout)',
      )

      arg (
         '-t', '--template', dest='template', default=argparse.SUPPRESS,
         flags=self.ARG_ADD_DEFAULT, metavar='<file|name>',
         help='template file or name for generating output',
      )

      arg (
         '-T', '--cgi-content-type', dest='cgi_content_type',
         default="text/html",
         flags=self.ARG_WITH_DEFAULT, metavar='<type>',
         help='cgi content type',
      )

      arg (
         '-M', '--module-root', dest='module_root',
         default=argparse.SUPPRESS, metavar="<dir>",
         type=couldbe_fs_dir,
         help="directory for storing cached templates",
      )

##      arg (
##         '-o', '--template-options', dest='template_options',
##         metavar='<option>', action='append',
##         help='pass arbitrary options to templates',
##      )

      return arg
   # --- end of setup_output_options (...) ---

   def parse_extra ( self ):
      self.parsed ['want_logging']   = False
      self.parsed ['load_main_only'] = True
   # --- end of parse_extra (...) ---


# --- end of RoverlayStatusArgumentParser (...) ---

class RoverlayMainArgumentParser ( RoverlayArgumentParser ):

   SETUP_TARGETS = (
      'version', 'actions', 'config', 'overlay', 'remote',
      'overlay_creation', 'setupdirs', 'additional_actions', 'misc',
   )
   PARSE_TARGETS = ( 'actions', 'config', )

   COMMAND_DESCRIPTION = collections.OrderedDict ((
      ( 'sync', 'sync repos' ),
      (
         'create',
         'create the overlay (implies sync, override with --no-sync)'
      ),
      (
         'depres_console',
         'run an interactive depres console (highly experimental)'
      ),
      ( 'depres', 'this is an alias to \'depres_console\'' ),
      ( 'nop', 'do nothing' ),
      (
         'apply_rules',
         'apply package rules verbosely and exit afterwards'
      ),
      ( 'setupdirs', 'create configured directories etc.' ),
      ( 'distmap_rebuild', 'regenerate distmap' ),
   ))

   DEFAULT_COMMAND = 'create'

   def parse_actions ( self ):
      command = self.parsed ['command']

      if command == 'nop':
         roverlay.core.die ( "Nothing to do!", roverlay.core.DIE.NOP )

      elif command in { 'setupdirs', 'distmap_rebuild' }:
         self.parsed ['want_logging']   = False
         self.parsed ['load_main_only'] = True

         if command == 'distmap_rebuild':
            self.do_extraconf ( False, 'OVERLAY.DISTDIR.verify' )

      else:
         self.parsed ['want_logging']   = True
         self.parsed ['load_main_only'] = False

         if command == 'sync' and not self.parsed.get ( 'sync', True ):
            roverlay.core.die (
               "sync command blocked by --no-sync opt.", roverlay.core.DIE.ARG
            )

      self.command = command
   # --- end of parse_actions (...) ---

   def setup_setupdirs ( self ):
      arg = self.add_argument_group (
         'setupdirs', title='setupdirs options',
      )

      arg (
         '--target-uid', dest='target_uid', default=os.getuid(),
         metavar='<uid>', type=is_uid, flags=self.ARG_WITH_DEFAULT,
         help='uid of the user that will run roverlay',
      )
      arg (
         '--target-gid', dest='target_gid', default=os.getgid(),
         metavar='<gid>', type=is_gid, flags=self.ARG_WITH_DEFAULT,
         help='gid of the user that will run roverlay',
      )


      return arg
   # --- end of setup_setupdirs (...) ---

   def setup_additional_actions ( self ):
      arg = self.add_argument_group (
         "additional_actions", title='additional actions',
      )

      arg (
         '--pc', '--print-config', dest='print_config',
         flags=self.ARG_OPT_IN,
         help="print config and exit",
      )

      arg (
         '--ppr', '--print-package-rules', dest='print_package_rules',
         flags=self.ARG_OPT_IN,
         help="print package rules after parsing them and exit",
      )

      arg (
         '--help-config', '--list-config-entries',
         dest='list_config_entries', flags=self.ARG_OPT_IN,
         help="list all known config entries and exit",
      )


      arg (
         '--dump-file', dest='dump_file', default='-',
         flags=self.ARG_WITH_DEFAULT|self.ARG_META_FILE,
         type=couldbe_stdout_or_file,
         help=(
            'file or stdout (\"-\") target for dumping information. '
            'Used by the \'apply_rules\' command.'
         ),
      )

      return arg
   # --- end of setup_additional_actions (...) ---
# --- end of RoverlayMainArgumentParser ---
