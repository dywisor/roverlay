# R overlay -- setup script, env for the "init" command
# -*- coding: utf-8 -*-
# Copyright (C) 2013 André Erdmann <dywi@mailerd.de>
# Distributed under the terms of the GNU General Public License;
# either version 2 of the License, or (at your option) any later version.

import os
import textwrap


import roverlay.fsutil

import roverlay.config.entrymap
import roverlay.config.entryutil

import roverlay.setupscript.baseenv


class SetupInitEnvironment (
   roverlay.setupscript.baseenv.SetupSubEnvironment
):

   # ( action_name, can_be_skipped )
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
      yield ( "additions dir",
         get_path_option ( 'additions_dir', self.setup_env.additions_dir )
      )

      import_config = get_option ( 'import_config' )
      if import_config == 'disable':
         yield ( "import config", "no" )
      elif self.setup_env.is_installed():
         yield ( "import config",
            "yes, "
            + self.IMPORT_CONFIG_DESC [import_config].format ( **fmt_vars )
         )
      else:
         yield (
            "import config",
            'no, standalone roverlay cannot import config '
            'with mode={!r}'.format ( import_config )
         )

      yield ( "enable default hooks", get_option ( 'want_default_hooks' ) )

      yield ( "overwrite hooks", self.setup_env.hook_overwrite.get_str() )

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
      mode = self.setup_env.options ['import_config']

      if mode == 'disable':
         self.info ( "config import: disabled.\n" )
         return
      elif not self.setup_env.is_installed():
         self.error ( "config import: disabled due to standalone mode.\n" )
         return

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
         self.setup_env.die ( "failed to enable hooks." )
   # --- end of do_enable_default_hooks (...) ---

# --- end of SetupInitEnvironment ---
