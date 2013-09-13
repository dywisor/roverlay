# R overlay -- setup script, runtime
# -*- coding: utf-8 -*-
# Copyright (C) 2013 André Erdmann <dywi@mailerd.de>
# Distributed under the terms of the GNU General Public License;
# either version 2 of the License, or (at your option) any later version.

from __future__ import print_function

import logging
import os
import sys
#import textwrap

import roverlay.argparser
import roverlay.argutil
import roverlay.fsutil
import roverlay.runtime

import roverlay.config.defconfig

import roverlay.setupscript.initenv
import roverlay.setupscript.hookenv



if sys.hexversion >= 0x3000000:
   read_user_input = input
else:
   read_user_input = raw_input



def setup_main_installed():
   return setup_main ( True )
# --- end of setup_main_installed (...) ---

def setup_main ( installed ):
   SetupEnvironment.run_default_main ( installed=installed )
   return os.EX_OK
# --- end of setup_main (...) ---

def arg_stdout_or_fs ( value ):
   if value == '-':
      return value
   else:
      return os.path.abspath ( os.path.expanduser ( value ) )
# --- end of arg_stdout_or_fs (...) ---


class SetupArgParser ( roverlay.argparser.RoverlayArgumentParser ):
   MULTIPLE_COMMANDS = False
   COMMAND_DESCRIPTION = {
      'init'     : 'initialize roverlay\'s config and filesystem layout',
      'mkconfig' : 'generate a config file',
      'hooks'    : 'manage hook files',
   }
   DEFAULT_COMMAND = "init"

   COMMANDS_WITH_PRETEND = frozenset ({ 'init', 'hooks', })

   SETUP_TARGETS = (
      'usage', 'version',
      'actions', 'setup', 'config', 'init', 'hooks',
   )
   PARSE_TARGETS = ( 'actions', 'setup', 'config', 'init', )


   def setup_setup ( self ):
      arg = self.setup_setup_minimal ( title='common options' )

      arg (
         '--output', '-O', metavar="<file|dir|->", dest='output',
         default='-', type=arg_stdout_or_fs,
         flags=self.ARG_WITH_DEFAULT,
         help='output file/dir/stream used by various commands (\'-\' for stdout)',
      )

      arg (
         '--pretend', '-p', dest='pretend',
         flags=self.ARG_WITH_DEFAULT|self.ARG_OPT_IN,
         help='show what would be done',
      )

      arg (
         '--ask', '-a', dest='wait_confirm',
         flags=self.ARG_WITH_DEFAULT|self.ARG_OPT_IN,
         help='get confirmation before actually doing anything',
      )

      return arg
   # --- end of setup_setup (...) ---

   def parse_setup ( self ):
      self.parse_setup_minimal()

      if self.parsed ['pretend']:
         for cmd in self.get_commands():
            if cmd not in self.__class__.COMMANDS_WITH_PRETEND:
               self.parser.exit (
                  "{!r} command does not support --pretend.".format ( cmd )
               )
   # --- end of parse_setup (...) ---

   def setup_config ( self ):
      arg = self.add_argument_group (
         "config", title="options for the main config file"
      )

      arg (
         '--expand-user', dest='config_expand_user',
         flags=self.ARG_WITH_DEFAULT|self.ARG_OPT_IN,
         help="expand \'~\' to the target user\'s home directory",
      )

      arg (
         '--additions-dir', '-A', dest='additions_dir',
         flags=self.ARG_WITH_DEFAULT|self.ARG_META_DIR,
         type=roverlay.argutil.couldbe_dirstr_existing,
         help=(
            'directory for user-provided content '
            '(patches, hand-written ebuilds, hooks)'
         ),
      )

      arg (
         '--variable', '-v', metavar="<key=\"value\">", dest='config_vars',
         default=[], action='append',
         type=roverlay.argutil.is_config_opt,
         help="additional variables",
      )

      arg (
         '--prjroot-relpath', dest='prjroot_relpath',
         flags=self.ARG_WITH_DEFAULT|self.ARG_OPT_IN,
         help=(
            'make --{work,data,conf}-root, --{conf,additions}-dir '
            'relative to ROVERLAY_PRJROOT (for distributing config files)'
         )
      )

      return arg
   # --- end of setup_config (...) ---

   def parse_config ( self ):
      for kv in self.parsed ['config_vars']:
         key, eq_sign, val = kv.partition('=')
         if key in { 'ADDITIONS_DIR', 'OVERLAY_ADDITIONS_DIR' }:
            self.parser.exit (
               'use \'--additions-dir {0}\' instead of '
               '\'--variable ADDITIONS_DIR={0}\'.'.format ( val )
            )

##      self.parsed ['config_vars'].append (
##         "ADDITIONS_DIR=" + self.parsed ['additions_dir']
##      )
   # --- end of parse_config (...) ---

   def setup_init ( self ):
      arg = self.add_argument_group (
         'init', title='options for the \'init\' command'
      )

      arg (
         '--enable-default-hooks', dest='want_default_hooks',
         default=True,
         flags=self.ARG_WITH_DEFAULT|self.ARG_OPT_IN,
         help='enable/update the default hooks',
      )

      arg (
         '--no-default-hooks', dest='want_default_hooks',
         flags=self.ARG_SHARED|self.ARG_OPT_OUT,
         help='disable the default hooks',
      )

      arg (
         '--import-config', '-I', dest='import_config',
         default="symlink",
         choices=[
            "disable",
            "symlink", "symlink=root",
            "symlink=dirs", "symlink=files",
            "copy"
         ],
         metavar='<mode>',
         flags=self.ARG_WITH_DEFAULT,
         help=(
            'choose whether and how --conf-root should be imported: '
             '%(choices)s'
         ),
      )

      arg (
         '--no-import-config', dest='import_config',
         action='store_const', const='disable',
         help='disable config import (same as \'--import-config disable\')',
      )


      arg (
         '--target-uid', dest='target_uid', default=os.getuid(),
         metavar='<uid>', type=roverlay.argutil.is_uid,
         flags=self.ARG_WITH_DEFAULT,
         help="uid of the user that will run roverlay",
      )

      arg (
         '--target-gid', dest='target_gid', default=os.getgid(),
         metavar='<gid>', type=roverlay.argutil.is_gid,
         flags=self.ARG_WITH_DEFAULT,
         help='gid of the user that will run roverlay',
      )

   # --- end of setup_init (...) ---

   def parse_init ( self ):
      my_uid = os.getuid()

      if my_uid and self.parsed ['target_uid'] != my_uid:
         if self.parsed ['pretend']:
            sys.stderr.write (
               "!!! --target-uid: users cannot configure other users.\n\n"
            )
         else:
            self.parser.exit (
               "--target-uid: users cannot configure other users."
            )
   # --- end of parse_init (...) ---

   def setup_hooks ( self ):
      arg = self.add_argument_group (
         "hooks", title="options for managing hooks"
      )

      arg (
         "--overwrite-hooks", dest='hook_overwrite',
         default="dead", const="links", nargs="?", metavar="<when>",
         choices=[ 'none', 'dead', 'links', 'all', ],
         flags=self.ARG_WITH_DEFAULT,
         help=(
            'control hook overwrite behavior '
            '(%(choices)s; \'%(const)s\' if specified without an arg)'
         ),
      )

      return arg
   # --- end of setup_hooks (...) ---

# --- end of SetupArgParser ---


class SetupEnvironment ( roverlay.runtime.IndependentRuntimeEnvironment ):

   LOG_LEVEL         = logging.INFO

   SHARED_DIR_MODE   = roverlay.fsutil.get_stat_mode ( "rwxrwxr-x" )
   PRIVATE_DIR_MODE  = roverlay.fsutil.get_stat_mode ( "rwxr-x---" )
   SHARED_FILE_MODE  = roverlay.fsutil.get_stat_mode ( "rw-rw-r--" )
   PRIVATE_FILE_MODE = roverlay.fsutil.get_stat_mode ( "rw-r-----" )

   def __init__ ( self, *args, **kwargs ):
      super ( SetupEnvironment, self ).__init__ ( *args, **kwargs )

      self.UID             = os.getuid()
      self.GID             = os.getgid()

      self.expanduser      = None
      self.fs_ops          = None
      self.fs_ops_virtual  = None

      self.want_chown      = None
      self.data_root       = None
      self.work_root       = None
      self.conf_root       = None
      self.user_conf_root  = None

# not used
#      COLUMNS = os.environ.get ( 'COLUMNS', 78 )
#
#      self.text_wrapper = textwrap.TextWrapper (
#         width=COLUMNS, initial_indent='', subsequent_indent='',
#         break_long_words=False, break_on_hyphens=False,
#      )
   # --- end of __init__ (...) ---

   def get_parser_defaults ( self ):
      if self.is_installed():
         instinfo = self.INSTALLINFO
         return {
            'work_root'         : instinfo ['workroot'],
            'data_root'         : instinfo ['libexec'],
            'conf_root'         : instinfo ['confroot'],
            'private_conf_root' : instinfo ['workroot'] + os.sep + 'config',
            'import_config'     : 'symlink=root',
            'additions_dir'     : instinfo ['workroot'] + os.sep + 'files',
         }
      else:
         assert self.prjroot
         prjroot = self.prjroot + os.sep
         return {
            'work_root'         : prjroot + 'workdir',
            'data_root'         : prjroot + 'files',
            'conf_root'         : prjroot + 'config',
            'private_conf_root' : prjroot + 'config',
            'import_config'     : 'disable',
            'additions_dir'     : prjroot + 'files',
         }
   # --- end of get_parser_defaults (...) ---

   def create_argparser ( self ):
      return SetupArgParser (
         description = 'roverlay setup script',
         defaults    = self.get_parser_defaults(),
         epilog      = (
            'Environment variables:\n'
            '* ROVERLAY_PRJROOT   - path to roverlay\'s source dir\n'
            '* ROVERLAY_INSTALLED - mark roverlay as installed (if set and not empty)\n'
         )
      )
   # --- end of create_argparser (...) ---

   def _get_config_roots ( self ):
      return (
         os.path.realpath ( self.conf_root ),
         os.path.realpath ( self.user_conf_root )
      )
   # --- end of get_config_roots (...) ---

   def get_user_config_root ( self ):
      conf_root, user_conf_root = self._get_config_roots()
      if conf_root == user_conf_root:
         return None
      else:
         return user_conf_root
   # --- end of get_user_config_root (...) ---

   def get_config_file_path ( self ):
      return (
         self.work_root + os.sep + self.access_constant ( 'config_file_name' )
      )
   # --- end of get_config_file_path (...) ---

   def create_new_target_config ( self ):
      return self.create_new_config (
         config_str=self.create_config_file ( expand_user=True )
      )
   # --- end of create_new_target_config (...) ---

   def _expanduser_pwd ( self, fspath ):
      return roverlay.fsutil.pwd_expanduser (
         fspath, self.options ['target_uid']
      )
   # --- end of _expanduser_pwd (...) ---

   def create_config_file ( self, expand_user=False ):
      def _get_prjroot_relpath ( fspath ):
         p = os.path.relpath ( fspath, self.prjroot )
         if p and ( p[0] != '.' or p == '.' ):
            return p
         else:
            return fspath
      # --- end of get_prjroot_relpath (...) ---

      get_prjroot_relpath = (
         _get_prjroot_relpath
            if ( self.options ['prjroot_relpath'] and self.prjroot )
         else (lambda p: p)
      )

      conf_creator = roverlay.config.defconfig.RoverlayConfigCreation (
         is_installed  = self.is_installed(),
         work_root     = get_prjroot_relpath (
            self.work_root if expand_user else self.options ['work_root']
         ),
         data_root     = get_prjroot_relpath (
            self.data_root if expand_user else self.options ['data_root']
         ),
         conf_root     = get_prjroot_relpath (
            self.user_conf_root if expand_user
            else self.options ['private_conf_root']
         ),
         additions_dir = get_prjroot_relpath (
            self.additions_dir if expand_user
            else self.options ['additions_dir']
         )
      )

      for kv in self.options ['config_vars']:
         key, sepa, value = kv.partition ( '=' )
         if not sepa:
            raise Exception ( "bad variable given: {!r}".format ( kv ) )
         elif key in { 'ADDITIONS_DIR', 'OVERLAY_ADDITIONS_DIR', }:
            conf_creator.set_option ( key, get_prjroot_relpath ( value ) )
         else:
            conf_creator.set_option ( key, value )

      return conf_creator.get_str()
   # --- end of create_config_file (...) ---

   def write_config_file ( self, output=None, expand_user=None ):
      config_file_str = self.create_config_file (
         expand_user = (
            self.options ['config_expand_user'] if expand_user is None
            else expand_user
         ),
      )
      if not output or output == '-':
         self.info ( config_file_str )
      else:
         with open ( output, 'wt' ) as FH:
            FH.write ( config_file_str )
   # --- end of write_config_file (...) ---

   def auto_reconfigure ( self ):
      self.reconfigure ( self.create_config_file() )
   # --- end of auto_reconfigure (...) ---

   def setup ( self ):
      self.setup_common ( allow_prjroot_missing=False )

      # ref
      options = self.options

      target_uid = options ['target_uid']
      target_gid = options ['target_gid']

      self.want_chown = ( target_uid != self.UID or target_gid != self.GID )

      if self.UID == target_uid:
         expanduser      = os.path.expanduser
         self.expanduser = os.path.expanduser
      else:
         expanduser      = self._expanduser_pwd
         self.expanduser = self._expanduser_pwd

      self.work_root      = expanduser ( options ['work_root'] )
      self.data_root      = expanduser ( options ['data_root'] )
      self.conf_root      = expanduser ( options ['conf_root'] )
      self.user_conf_root = expanduser ( options ['private_conf_root'] )
      self.additions_dir  = expanduser ( options ['additions_dir'] )
      self.hook_overwrite = (
         roverlay.setupscript.hookenv.HookOverwriteControl.from_str (
            options ['hook_overwrite']
         )
      )


      self.fs_ops_virtual = {
         'private_dir': roverlay.fsutil.VirtualFsOperations (
            uid=target_uid, gid=target_gid, mode=self.PRIVATE_DIR_MODE,
         ),
         'shared_dir': roverlay.fsutil.VirtualFsOperations (
            uid=target_uid, gid=target_gid, mode=self.SHARED_DIR_MODE,
         ),
         'private_file': roverlay.fsutil.VirtualFsOperations (
            uid=target_uid, gid=target_gid, mode=self.PRIVATE_FILE_MODE,
         ),
         'shared_file': roverlay.fsutil.VirtualFsOperations (
            uid=target_uid, gid=target_gid, mode=self.SHARED_FILE_MODE,
         ),
      }

      if options ['pretend']:
         self.fs_ops = self.fs_ops_virtual
      else:
         self.fs_ops =  {
            'private_dir': roverlay.fsutil.FsOperations (
               uid=target_uid, gid=target_gid, mode=self.PRIVATE_DIR_MODE,
            ),
            'shared_dir': roverlay.fsutil.FsOperations (
               uid=target_uid, gid=target_gid, mode=self.SHARED_DIR_MODE,
            ),
            'private_file': roverlay.fsutil.FsOperations (
               uid=target_uid, gid=target_gid, mode=self.PRIVATE_FILE_MODE,
            ),
            'shared_file': roverlay.fsutil.FsOperations (
               uid=target_uid, gid=target_gid, mode=self.SHARED_FILE_MODE,
            ),
         }

      # bind fs_ops
      self.private_dir  = self.fs_ops ['private_dir']
      self.shared_dir   = self.fs_ops ['shared_dir']
      self.private_file = self.fs_ops ['private_file']
      self.shared_file  = self.fs_ops ['shared_file']
   # --- end of setup (...) ---

   def wait_confirm ( self,
      message=None, message_inline=None,
      prepend_newline=True, append_newline=True
   ):
      try:
         if prepend_newline:
            self.info ( '\n' )

         if message is not None:
            self.info ( str ( message ) + '\n' )

         if message_inline:
            self.info (
               "Press Enter to continue ({!s}) ... ".format ( message_inline )
            )
         else:
            self.info ( "Press Enter to continue ... " )

         self.stdout.flush()

         ret = read_user_input().strip()

      except ( KeyboardInterrupt, EOFError ):
         self.info ( "\n" )
         sys.exit ( 130 )
      else:
         if append_newline:
            self.info ( '\n' )

         return ret
   # --- end of wait_confirm (...) ---

   def wait_confirm_can_skip ( self,
      SKIP_WORDS=frozenset({ 'skip', 'no', 'n'}), **kwargs
   ):
      assert 'message_inline' not in kwargs

      if self.options ['wait_confirm']:

         user_reply = self.wait_confirm (
            message_inline="type {} to skip this step".format (
               '/'.join ( repr( word ) for word in sorted( SKIP_WORDS ) )
            ),
            **kwargs
         )

         return user_reply.lower() not in SKIP_WORDS
      else:
         return True
   # --- end of wait_confirm (...) ---

   def get_init_env ( self ):
      return roverlay.setupscript.initenv.SetupInitEnvironment ( self )
   # --- end of get_init_env (...) ---

   def get_hook_env ( self ):
      return roverlay.setupscript.hookenv.SetupHookEnvironment ( self )
   # --- end of get_hook_env (...) ---

   def default_main ( self ):
      if self.wants_command ( "mkconfig" ):
         self.write_config_file ( self.options ['output'] )
      elif self.wants_command ( "hooks" ):
         self.get_hook_env().run()
      elif self.wants_command ( "init" ):
         self.get_init_env().run()
   # --- end of default_main (...) ---

# --- end of SetupEnvironment ---
