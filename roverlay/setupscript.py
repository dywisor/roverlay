# R overlay -- setup script
# -*- coding: utf-8 -*-

from __future__ import print_function

import argparse
import collections
import errno
import logging
import os
import shutil
import stat
import sys
import textwrap

import roverlay.argutil
import roverlay.argparser
import roverlay.fsutil
import roverlay.runtime

import roverlay.config.defconfig
import roverlay.config.entrymap
import roverlay.config.entryutil

import roverlay.static.hookinfo

import roverlay.util.counter

if sys.hexversion >= 0x3000000:
   read_user_input = input
else:
   read_user_input = raw_input






def arg_stdout_or_fs ( value ):
   if value == '-':
      return value
   else:
      return os.path.abspath ( os.path.expanduser ( value ) )
# --- end of arg_stdout_or_fs (...) ---




class SetupArgParser ( roverlay.argparser.RoverlayArgumentParser ):
   MULTIPLE_COMMANDS = False
   COMMAND_DESCRIPTION = {
      'init':     'initialize roverlay\'s config and filesystem layout',
      'mkconfig': 'generate a config file',
   }
   DEFAULT_COMMAND = "init"

   COMMANDS_WITH_PRETEND = frozenset ({ 'init', })

   SETUP_TARGETS = ( 'version', 'actions', 'setup', 'config', 'init', )
   PARSE_TARGETS = ( 'actions', 'setup', 'init', )


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
         '--variable', '-v', metavar="<key=\"value\">", dest='config_vars',
         default=[], action='append',
         type=roverlay.argutil.is_config_opt,
         help="additional variables",
      )

      return arg
   # --- end of setup_config (...) ---

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
   # --- end of __init__ (...) ---

   def create_argparser ( self ):
      instinfo = self.access_constant ( 'INSTALLINFO' )

      return SetupArgParser (
         description = 'roverlay setup script',
         defaults    = {
            'work_root'         : instinfo ['workroot'],
            'data_root'         : instinfo ['libexec'],
            'conf_root'         : instinfo ['confroot'],
            'private_conf_root' : instinfo ['workroot'] + os.sep + 'config',
            'import_config'     : 'symlink=root',
         },
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
      conf_creator = roverlay.config.defconfig.RoverlayConfigCreation (
         work_root = (
            self.work_root if expand_user else self.options ['work_root']
         ),
         data_root = (
            self.data_root if expand_user else self.options ['data_root']
         ),
         conf_root = (
            self.user_conf_root if expand_user
            else self.options ['private_conf_root']
         ),
      )

      for kv in self.options ['config_vars']:
         key, sepa, value = kv.partition ( '=' )
         if not sepa:
            raise Exception ( "bad variable given: {!r}".format ( kv ) )
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
      self.PWD_INITIAL = os.getcwd()
      self.setup_common()

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
      return SetupInitEnvironment ( self )
   # --- end of get_init_env (...) ---

   def get_hook_env ( self ):
      return SetupHookEnvironment ( self )
   # --- end of get_hook_env (...) ---

# --- end of SetupEnvironment ---


class SetupSubEnvironment ( object ):

   NEEDS_CONFIG_TREE = False

   ACTIONS = None

   def __init__ ( self, setup_env ):
      super ( SetupSubEnvironment, self ).__init__()

      self.setup_env = setup_env
      self.stdout    = setup_env.stdout
      self.stderr    = setup_env.stderr
      self.info      = setup_env.info
      self.error     = setup_env.error

      if self.NEEDS_CONFIG_TREE:
         self.config = self.setup_env.create_new_target_config()
      else:
         self.config = None

      self.setup()
   # --- end of __init__ (...) ---

   def setup ( self ):
      pass
   # --- end of setup (...) ---

   def run ( self, steps_to_skip=None, verbose_skip=True, steps=None ):
      pretend = self.setup_env.options ['pretend']
      ACTIONS = steps if steps is not None else self.ACTIONS

      if ACTIONS:
         if steps_to_skip:
            methods_to_call = [
               (
                  None if item[0] in steps_to_skip
                  else getattr ( self, 'do_' + item[0] )
               ) for item in ACTIONS
            ]
         else:
            methods_to_call = [
               getattr ( self, 'do_' + item[0] ) for item in ACTIONS
            ]

         wait_confirm_can_skip = self.setup_env.wait_confirm_can_skip


         for method, action in zip ( methods_to_call, ACTIONS ):
            if method is None:
               if verbose_skip:
                  self.info ( "{}: skipped.\n".format ( action[0] ) )

            elif not action[1]:
               method ( pretend=pretend )

            elif wait_confirm_can_skip (
               message=method.__doc__, append_newline=False
            ):
               method ( pretend=pretend )
            else:
               self.info ( "skipped.\n" )

      else:
         raise NotImplementedError (
            "{}.{}()".format ( self.__class__.__name__, "do_all" )
         )
   # --- end of run (...) ---


# --- end of SetupSubEnvironment ---


class SetupInitEnvironment ( SetupSubEnvironment ):

   ACTIONS = (
      ( 'pretend', False ),
      ( 'prepare_config_file', False ),
      ( 'import_config', True ),
      ( 'setupdirs', True ),
      ( 'write_config_file', True ),
      ( 'enable_default_hooks', True ),
   )

   NEEDS_CONFIG_TREE = True

   def setup ( self ):
      self.config_file_str = None
   # --- end of setup (...) ---

   IMPORT_CONFIG_DESC = {
      'disable'       : False,
      'symlink'       : 'symlink {conf_root} to {user_conf_root}',
      'symlink=root'  : 'symlink {conf_root} to {user_conf_root}',
      'symlink=dirs'  : (
         'symlink files/dirs from {conf_root} to {user_conf_root}/'
      ),
      'symlink=files' : (
         'recursively copy {conf_root} to {user_conf_root}, '
         'but symlink files instead of copying them'
      ),
      'copy'          : 'recursively copy {conf_root} to {user_conf_root}',
   }

   def gen_pretend_options ( self ):
      options = self.setup_env.options

      def get_option ( key ):
         val = options [key]
         if isinstance ( val, str ):
            return val
         elif hasattr ( val, '__iter__' ):
            return ' '.join ( str(x) for x in val )
         elif isinstance ( val, bool ):
            return "yes" if val else "no"
         elif val is None:
            return "<undef>"
         else:
            return str ( val )
      # --- end of get_option (...) ---

      comment_path    = lambda a, b: a if a == b else ( a + ' (' + b + ')' )
      get_path_option = lambda k, b: comment_path ( get_option ( k ), b )

      fmt_vars = {
         'conf_root'     : options ['conf_root'],
         'user_conf_root': options ['private_conf_root']
      }

      yield ( "user/uid",  get_option ( 'target_uid' ) )
      yield ( "group/gid", get_option ( 'target_gid' ) )

      yield ( "work root",
         get_path_option ( 'work_root', self.setup_env.work_root )
      )
      yield ( "data root",
         get_path_option ( 'data_root', self.setup_env.data_root )
      )
      yield ( "roverlay\'s config root",
         get_path_option ( 'conf_root', self.setup_env.conf_root )
      )
      yield ( "user\'s config root",
         get_path_option ( 'private_conf_root', self.setup_env.user_conf_root )
      )

      import_config = get_option ( 'import_config' )
      if import_config == 'disable':
         yield ( "import config", "no" )
      else:
         yield ( "import config",
            "yes, "
            + self.IMPORT_CONFIG_DESC [import_config].format ( **fmt_vars )
         )

      yield ( "enable default hooks", get_option ( 'want_default_hooks' ) )
      yield ( "additional config variables", get_option ( 'config_vars' ) )
   # --- end of gen_pretend_options (...) ---

   def gen_pretend_lines ( self, append_newline=True ):
      options  = list ( self.gen_pretend_options() )
      COLUMNS  = os.environ.get ( 'COLUMNS', 78 )
      desc_len = min ( COLUMNS // 2,
         1 + max ( len(desc) for desc, value in options )
      )

      line_wrapper = textwrap.TextWrapper (
         width=COLUMNS, initial_indent='',
         subsequent_indent=( (desc_len+5) * ' ' ),
         break_long_words=False, break_on_hyphens=False,
      )


      yield 'Configuration:'
      for desc, value in options:
         yield line_wrapper.fill (
            "- {desc:<{l}}: {value}".format (
               desc=desc, l=desc_len, value=value,
            )
         )

      if append_newline:
         yield ""
   # --- end of gen_pretend_lines (...) ---

   def do_pretend ( self, pretend ):
      """Shows what would be done."""
      self.info ( '\n'.join ( self.gen_pretend_lines() ) + '\n' )
   # --- end of do_pretend (...) ---

   def do_prepare_config_file ( self, pretend ):
      """Creates the config file (in memory)."""
      self.config_file_str = self.setup_env.create_config_file (
         expand_user=self.setup_env.options ['config_expand_user']
      )
   # --- end of do_prepare_config_file (...) ---

   def do_import_config ( self, pretend ):
      """Imports the config."""
      mode           = self.setup_env.options ['import_config']
      fs_ops         = self.setup_env.private_dir
      user_conf_root = self.setup_env.get_user_config_root()
      # assert os.path.isdir ( os.path.dirname(user_conf_root) == work_root )

      if user_conf_root is None and (
         fs_ops.unlink ( self.setup_env.user_conf_root )
      ):
         # config_root was a symlink

         if pretend:
            user_conf_root = self.setup_env.user_conf_root
         else:
            user_conf_root = self.setup_env.get_user_config_root()

      # -- end if


      if user_conf_root is None:
         self.info (
            "user has no private config directory - skipping config import.\n"
         )

      elif mode in { 'symlink=root', 'symlink' }:
         if not fs_ops.wipe ( user_conf_root ):
            self.setup_env.die (
               "failed to remove {!r}.\n".format ( user_conf_root )
            )
         elif not fs_ops.symlink ( self.setup_env.conf_root, user_conf_root ):
            self.setup_env.die (
               "could not create symlink to {!r}.".format (
                  self.setup_env.conf_root
               )
            )


         pass
      else:
         raise NotImplementedError ( mode )
   # --- end of do_import_config (...) ---

   def do_setupdirs ( self, pretend ):
      """Creates directories with proper permissions."""
      create_subdir_check = roverlay.fsutil.create_subdir_check
      config              = self.config
      find_config_path    = roverlay.config.entryutil.find_config_path
      dodir_private       = self.setup_env.private_dir.dodir
      dodir_shared        = self.setup_env.shared_dir.dodir


      WANT_USERDIR = roverlay.config.entrymap.WANT_USERDIR
      WANT_PRIVATE = roverlay.config.entrymap.WANT_PRIVATE
      WANT_FILEDIR = roverlay.config.entrymap.WANT_FILEDIR

      listlike    = lambda a: (
         hasattr(a, '__iter__') and not isinstance(a, str)
      )
      iter_values = lambda b: (
         () if b is None else (b if listlike(b) else ( b, ))
      )

      dirs_exclude = [
         create_subdir_check ( self.setup_env.conf_root ),
         create_subdir_check ( self.setup_env.data_root ),
      ]
      if self.setup_env.get_user_config_root() is None:
         dirs_exclude.append (
            create_subdir_check ( self.setup_env.user_conf_root )
         )
      else:
         print ( self.setup_env.get_user_config_root() )

      # don't print exclude/skip messages more than once per dir
      dirs_already_excluded = set()

      private_dirs       = set()
      private_dirs_chown = set()
      shared_dirs        = set()
      shared_dirs_chown  = set()

      # it's not necessary to create all of the listed dirs because some of
      # them are automatically created at runtime, but doing so results in
      # a (mostly) complete filesystem layout
      #
      for config_key, entry in (
         roverlay.config.entrymap.CONFIG_ENTRY_MAP.items()
      ):
         if isinstance ( entry, dict ) and 'want_dir_create' in entry:
            for value in iter_values (
               config.get ( find_config_path ( config_key ), None )
            ):
               dirmask = entry ['want_dir_create']
               dirpath = (
                  os.path.dirname ( value.rstrip ( os.sep ) )
                  if dirmask & WANT_FILEDIR else value.rstrip ( os.sep )
               )

               if not dirpath or dirpath in dirs_already_excluded:
                  pass

               elif any ( ex ( dirpath ) for ex in dirs_exclude ):
                  self.info (
                     "setupdirs: excluding {!r}\n".format ( dirpath )
                  )
                  dirs_already_excluded.add ( dirpath )

               elif os.path.islink ( dirpath ):
                  self.info (
                     '{!r} is a symlink - skipping setupdir '
                     'actions.\n'.format ( dirpath )
                  )
                  dirs_already_excluded.add ( dirpath )

               elif dirmask & WANT_USERDIR:
                  if dirmask & WANT_PRIVATE:
                     private_dirs_chown.add ( dirpath )
                  else:
                     shared_dirs_chown.add ( dirpath )

               elif dirmask & WANT_PRIVATE:
                  private_dirs.add ( dirpath )

               else:
                  shared_dirs.add ( dirpath )
      # -- end for


      private_dirs      -= private_dirs_chown
      shared_dirs_chown -= private_dirs
      shared_dirs       -= shared_dirs_chown

      for dirpath in shared_dirs:
         dodir_shared ( dirpath, chown=False )

      for dirpath in shared_dirs_chown:
         dodir_shared ( dirpath, chown=True )

      for dirpath in private_dirs:
         dodir_private ( dirpath, chown=False )

      for dirpath in private_dirs_chown:
         dodir_private ( dirpath, chown=True )

      self.setup_env.private_dir.chmod_chown ( self.setup_env.work_root )
   # --- end of do_setupdirs (...) ---

   def do_write_config_file ( self, pretend ):
      """Writes the config file to disk."""
      cfile = self.setup_env.get_config_file_path()
      if not self.config_file_str:
         self.setup_env.die ( "no config file created!" )
      elif pretend:
         self.info ( "Would write config file to {!r}.\n".format ( cfile ) )
      else:
         with open ( cfile, 'wt' ) as FH:
            FH.write ( self.config_file_str )

      self.setup_env.private_file.chmod_chown ( cfile )
   # --- end of do_write_config_file (...) ---

   def do_enable_default_hooks ( self, pretend ):
      """Enables the default hooks, e.g. git history creation."""
      hook_env = self.setup_env.get_hook_env()
      if not hook_env.enable_defaults():
         die ( "failed to enable hooks." )
   # --- end of do_enable_default_hooks (...) ---

# --- end of SetupInitEnvironment ---


class HookScript ( object ):

   def __init__ ( self, fspath, filename=None ):
      super ( HookScript, self ).__init__()
      fname = (
         filename if filename is not None else os.path.basename ( fspath )
      )

      self.fspath  = fspath
      self.name    = os.path.splitext ( fname )[0] or fname
      static_entry = roverlay.static.hookinfo.get ( self.name, None )

      if static_entry is not None:
         self.default_events = static_entry[0]
         self.priority       = static_entry[1]
         self.is_hidden      = static_entry[2]
      else:
         self.default_events = False
         self.priority       = None
         self.is_hidden      = False
   # --- end of __init__ (...) ---

   def is_visible ( self ):
      return not self.is_hidden and (
         self.priority is None or self.priority >= 0
      )
   # --- end of is_visible (...) ---

   def __str__ ( self ):
      yesno = lambda k: 'y' if k else 'n'
      return "<{cls} {name!r}, hidden={h} prio={p}>".format (
         cls=self.__class__.__name__,
         name=self.name,
         h=yesno ( self.is_hidden ),
         p=(
            "auto" if self.priority is None else
               ( "IGNORE" if self.priority < 0 else self.priority )
         ),
      )
   # --- end of __str__ (...) ---

   def set_priority_from_generator ( self, number_gen, only_if_unset=True ):
      if self.priority is None:
         self.priority = next ( number_gen )
         return True
      elif only_if_unset or self.priority < 0:
         return False
      else:
         self.priority = next ( number_gen )
         return True
   # --- end of set_priority_from_generator (...) ---

   def get_dest_name ( self, file_ext='.sh', digit_len=2 ):
      # file_ext has to be .sh, else the script doesn't get recognized
      # by mux.sh

      prio = self.priority
      if prio is None or prio < 0:
         raise AssertionError ( "hook script has no priority." )

      return "{prio:0>{l}d}-{fname}{f_ext}".format (
         prio=prio, fname=self.name, f_ext=file_ext, l=digit_len,
      )
   # --- end of get_dest_name (...) ---


# --- end of HookScript ---


class HookScriptDir ( object ):

   def __init__ ( self, root ):
      super ( HookScriptDir, self ).__init__()

      self.root      = root
      self._scripts  = collections.OrderedDict()
   # --- end of __init__ (...) ---

   def __bool__ ( self ):
      return bool ( self._scripts )
   # --- end of __bool__ (...) ---

   def get_script ( self, name ):
      script = self._scripts [name]
      return script if script.is_visible() else None
   # --- end of get_scripts (...) ---

   def iter_default_scripts ( self, unpack=False ):
      if unpack:
         for script in self._scripts.values():
            if script.default_events:
               for event in script.default_events:
                  yield ( event, script )
      else:
         for script in self._scripts.values():
            if script.default_events:
               yield script
   # --- end of iter_default_scripts (...) ---

   def get_default_scripts ( self ):
      scripts = dict()
      for event, script in self.iter_default_scripts ( unpack=True ):
         if event not in scripts:
            scripts [event] = [ script ]
         else:
            scripts [event].append ( script )

      return scripts
   # --- end of get_default_scripts (...) ---

   def iter_scripts ( self ):
      for script in self._scripts.values():
         if script.is_visible():
            yield script
   # --- end of iter_scripts (...) ---

   def scan ( self ):
      root = self.root
      try:
         filenames = sorted ( os.listdir ( root ) )
      except OSError as oserr:
         if oserr.errno != errno.ENOENT:
            raise

      else:
         for fname in filenames:
            fspath = root + os.sep + fname
            if os.path.isfile ( fspath ):
               script_obj = HookScript ( fspath, fname )
               self._scripts [script_obj.name] = script_obj
   # --- end of scan (...) ---

# --- end of HookScriptDir ---


class SetupHookEnvironment ( SetupSubEnvironment ):

   NEEDS_CONFIG_TREE = True

   def setup ( self ):
      additions_dir = self.config.get ( 'OVERLAY.additions_dir', None )
      if additions_dir:
         self.user_hook_root = os.path.join ( additions_dir, 'hooks' )
         self.writable       = self.setup_env.private_file.check_writable (
            self.user_hook_root + os.sep + '.keep'
         )
      else:
         self.user_hook_root = None
         self.writable       = None

      self.hook_root = HookScriptDir (
         os.path.join ( self.setup_env.data_root, 'hooks' )
      )
      self.hook_root.scan()
      self._prio_gen = roverlay.util.counter.UnsafeCounter ( 30 )
   # --- end of setup (...) ---

   def _link_hook ( self, source, link ):
      if os.path.lexists ( link ):
         linkdest = os.path.realpath ( link )

         message = 'Skipping activation of hook {!r} - '.format ( link )

         if linkdest == source or linkdest == os.path.realpath ( source ):
            self.info ( message + "already set up.\n" )
            return True

         elif link != linkdest:
            # symlink or link was relative
            self.error ( message + "is a link to another file.\n" )
         else:
            self.error ( message + "exists, but is not a link.\n" )

         return None
      else:
         return self.setup_env.private_file.symlink ( source, link )
   # --- end of _link_hook (...) ---

   def link_hooks_v ( self, event_name, hooks ):
      success = False

      if self.writable and self.user_hook_root:
         destdir = self.user_hook_root + os.sep + event_name
         self.setup_env.private_dir.dodir ( destdir )

         to_link = []
         for script in hooks:
            script.set_priority_from_generator ( self._prio_gen )
            to_link.append (
               ( script.fspath, destdir + os.sep + script.get_dest_name() )
            )

         success = True
         for source, link_name in to_link:
            if self._link_hook ( source, link_name ) is False:
               success = False
      # -- end if

      return success
   # --- end of link_hooks_v (...) ---

   def enable_defaults ( self ):
      # not strict: missing hooks are ignored
      success = False
      if self.hook_root:
         success = True
         default_hooks = self.hook_root.get_default_scripts()
         for event, hooks in default_hooks.items():
            if not self.link_hooks_v ( event, hooks ):
               success = False
      # -- end if

      return success
   # --- end of enable_defaults (...) ---


# --- end of SetupHookEnvironment ---


def setup_main():
   env = SetupEnvironment()
   env.setup()

   if env.wants_command ( "mkconfig" ):
      env.write_config_file ( env.options ['output'] )
   elif env.wants_command ( "init" ):
      env.get_init_env().run()


# --- end of setup_main (...) ---
