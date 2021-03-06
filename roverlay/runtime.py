# R overlay -- runtime env
# -*- coding: utf-8 -*-
# Copyright (C) 2013 André Erdmann <dywi@mailerd.de>
# Distributed under the terms of the GNU General Public License;
# either version 2 of the License, or (at your option) any later version.

import functools
import logging
import errno
import os
import sys


import roverlay.argparser
import roverlay.core
import roverlay.fsutil
import roverlay.hook
import roverlay.remote.repolist
import roverlay.stats.collector
import roverlay.util.objects
import roverlay.recipe.easylogger

import roverlay.packagerules.generators.addition_control
from roverlay.packagerules.generators.addition_control import \
   create_addition_control_package_rule

import roverlay.config.tree
import roverlay.config.const

from roverlay.core import DIE, die

# TODO: move/merge roverlay.core.DIE into runtime env


class MinimalRuntimeEnvironment ( object ):

   HLINE = 79 * '-'

   def __init__ ( self ):
      super ( MinimalRuntimeEnvironment, self ).__init__()
      self.logger = None
      self.bind_logger ( logging.getLogger() )
   # -- end of __init__ (...) ---

   def bind_logger ( self, logger ):
      self.logger       = logger
      self.log_debug    = logger.debug
      self.log_info     = logger.info
      self.log_warn     = logger.warn
      self.log_warning  = logger.warning
      self.log_error    = logger.error
      self.log_critical = logger.critical
   # --- end of bind_logger (...) ---

   @roverlay.util.objects.abstractmethod
   def setup ( self ):
      pass

   def die ( self, msg=None, code=None ):
      """
      Calls syst.exit (code:=1) after printing a message (if any).
      """
      code = 1 if code is None else code
      if msg is not None:
         sys.stderr.write ( msg + "\n" )
#      else:
#         sys.stderr.write ( "died.\n" )
      sys.exit ( code )
   # --- end of die (...) ---

# --- end of MinimalRuntimeEnvironment ---


class RuntimeEnvironmentBase ( MinimalRuntimeEnvironment ):

   ARG_PARSER_CLS  = None
   KEEP_ARG_PARSER = False

   def __init__ ( self,
      installed,
      hide_exceptions=False,
      config_file_name=roverlay.core.DEFAULT_CONFIG_FILE_NAME
   ):
      super ( RuntimeEnvironmentBase, self ).__init__()
      self.installed         = bool ( installed )
      self.hide_exceptions   = bool ( hide_exceptions )
      self.config_file_name  = str ( config_file_name )

      self.stats             = roverlay.stats.collector.static
      self.config            = None
      self.additional_config = None
      self.options           = None
      self.command           = None
   # --- end of __init__ (...) ---

   def setup ( self ):
      roverlay.core.setup_initial_logger()
      self.stats.time.begin ( "setup" )
      if self.hide_exceptions:
         try:
            self.do_setup()
         except:
            die ( "failed to initialize runtime environment." )
      else:
         self.do_setup()
      self.stats.time.end ( "setup" )
   # --- end of setup (...) ---

   def do_setup_parser ( self ):
      parser = self.ARG_PARSER_CLS (
         defaults={
            'config_file': roverlay.core.locate_config_file (
               self.installed, self.config_file_name
            )
         }
      )
      parser.setup()
      parser.parse()
      parser.do_extraconf ( self.installed, 'installed' )

      self.command           = getattr ( parser, 'command', None )
      self.options           = parser.parsed
      self.additional_config = parser.extra_conf

      if self.KEEP_ARG_PARSER:
         self.parser = parser
   # --- end of do_setup_parser (...) ---

   def do_setup_config ( self ):
      # set console logging _before_ loading the config file so that
      # ConfigTree (debug) messages are visible
      #
      console_log_level = functools.reduce (
         ( lambda d, k: dict.get ( d, k ) if d else None ),
         [ "LOG", "CONSOLE", "level" ],
         self.additional_config
      )

      if console_log_level:
         roverlay.recipe.easylogger.force_reset()
         roverlay.recipe.easylogger.setup_initial ( log_level=console_log_level )

      try:
         self.config = roverlay.core.load_config_file (
            self.options ['config_file'],
            extraconf      = self.additional_config,
            setup_logger   = self.options.get ( 'want_logging', False ),
            load_main_only = self.options.get ( 'load_main_only', True ),
         )
      except:
         if self.hide_exceptions:
            die (
               "Cannot load config file {!r}".format (
                  self.options ['config_file']
               ),
               DIE.CONFIG
            )
         else:
            raise
   # --- end of do_setup_config (...) ---

   def do_setup ( self ):
      self.do_setup_parser()
      self.do_setup_config()
   # --- end of do_setup (...) ---

# --- end of RuntimeEnvironmentBase (...) ---

class RuntimeEnvironment ( RuntimeEnvironmentBase ):

   ARG_PARSER_CLS = (
      roverlay.argparser.RoverlayMainArgumentParser.create_new_parser
   )

   def __init__ ( self, installed, *args, **kw ):
      super ( RuntimeEnvironment, self ).__init__ ( installed, *args, **kw )

      self.actions_done     = set()
      self.command          = None

      self.stats_db_file    = None
      self.want_db_commit   = False

      self._repo_list       = None
      self._overlay_creator = None
   # --- end of __init__ (...) ---

   def get_repo_list ( self ):
      if self._repo_list is None:
         self._repo_list = roverlay.remote.repolist.RepoList (
            sync_enabled   = not self.config.get_or_fail ( 'nosync' ),
            force_distroot = self.options.get ( 'force_distroot' )
         )
      return self._repo_list
   # --- end of get_repo_list (...) ---

   def get_overlay_creator ( self ):
      if self._overlay_creator is None:
         self._overlay_creator = roverlay.overlay.creator.OverlayCreator (
            skip_manifest           = not self.options ['manifest'],
            incremental             = self.options ['incremental'],
            allow_write             = self.options ['write_overlay'],
            immediate_ebuild_writes = self.options ['immediate_ebuild_writes'],
            repo_id_map = self.get_repo_list().create_repo_identifier_map(),
         )
      return self._overlay_creator
   # --- end of get_overlay_creator (...) ---

   def create_addition_control_rules ( self, default_category=None ):
      """Creates addition control package rules from cmdline/config.

      Returns: a package rule object or None

      arguments:
      * default_category -- name of the default category
                             Can be None/"false", in which case it is
                             queried from self.config
                             Defaults to None.
      """
      kwargs = {}
      def add_key ( k, _kwargs=kwargs, _options=self.options ):
         _kwargs [k] = _options [k]

      add_key ( "cmdline_package_revbump_on_collision" )
      add_key ( "cmdline_package_force_replace" )
      add_key ( "cmdline_package_replace_only" )

      add_key ( "file_package_extended" )
      add_key ( "file_ebuild_extended"  )

      return create_addition_control_package_rule (
         (
            default_category
               or self.config.get_or_fail ( 'OVERLAY.category' )
         ),
         **kwargs
      )
   # --- end of create_addition_control_rules (...) ---

   def add_addition_control_rules (
      self, package_rules, default_category=None
   ):
      """Adds addition control rules to the given package rules object.

      Returns True if add-policy rules have been added and False if not
      (i.e. no rules configured).

      See also create_addition_control_rules().

      arguments:
      * package_rules    --
      * default_category --
      """
      add_control_rule = self.create_addition_control_rules (
         default_category = default_category
      )

      if add_control_rule:
         package_rules.append_rule ( add_control_rule )
         return True
      else:
         return False
   # --- end of add_addition_control_rules (...) ---

   def add_addition_control_to_overlay_creator ( self ):
      """Adds addition control to the overlay creator.
      Currently, this is limited to add-policy package rules.

      The overlay creator and its package rules have to be initialized
      with get_overlay_creator() before calling this method.

      Returns True if any addition control has been added, else False.

      arguments: none
      """
      if not self._overlay_creator:
         raise AssertionError ( "overlay creator not initialized." )
      elif not getattr ( self._overlay_creator, 'package_rules', None ):
         raise AssertionError ( "overlay creator has no package rules." )
      # --

      return self.add_addition_control_rules (
         self._overlay_creator.package_rules,
         self._overlay_creator.overlay.default_category,
      )

      # + add addition_control object [FUTURE]

   # --- end of add_addition_control_to_overlay_creator (...) ---


   def do_setup ( self ):
      self.do_setup_parser()
      self.do_setup_config()

      self.stats_db_file = self.config.get ( 'STATS.dbfile', None )

      # want_logging <=> <have a command that uses hooks>
      if self.options ['want_logging']:
         roverlay.hook.setup()
   # --- end of do_setup (...) ---

   def setup_database ( self ):
      if self.stats_db_file:
         try:
            self.stats.setup_database ( self.config )

         except OSError as oserr:
            if oserr.errno == errno.ENOENT:
               self.stats_db_file = None
               self.logger.error (
                  'database not available. '
                  'Persistent stats collection has been disabled.'
               )
               return False
            else:
               raise

         else:
            return True
      else:
         return False
   # --- end of setup_database (...) ---

   def write_database ( self, hook_event=True ):
      if self.stats_db_file and self.want_db_commit:
         self.stats.write_database()
         if hook_event:
            roverlay.hook.run ( "db_written" )
         return True
      else:
         return False
   # --- end of write_database (...) ---

   def dump_stats ( self, stream=None, force=False ):
      if force or self.options ['dump_stats']:
         cout = sys.stdout.write if stream is None else stream.write

         cout ( "\n{:-^60}\n".format ( " stats dump " ) )
         cout ( str ( self.stats ) )
         cout ( "\n{:-^60}\n".format ( " end stats dump " ) )

         return True
      else:
         return False
   # --- end of dump_stats (...) ---

   def set_action_done ( self, action ):
      self.actions_done.add ( action )
   # --- end of set_action_done (...) ---

   def action_done ( self, action ):
      return action in self.actions_done
   # --- end of action_done (...) ---

   def want_command ( self, command ):
      return command == self.command
      ##and command not in self.actions_done
   # --- end of want_command (...) ---

   def option ( self, key, fallback=None ):
      return self.options.get ( key, fallback )
   # --- end of option (...) ---

   def optionally ( self, func, key, *args, **kwargs ):
      if self.options.get ( key, False ):
         return func ( *args, **kwargs )
      else:
         return None
   # --- end of optionally (...) ---

# --- end of RuntimeEnvironment ---


class IndependentRuntimeEnvironment ( MinimalRuntimeEnvironment ):

   LOG_FORMAT = None
   LOG_LEVEL  = None

   @classmethod
   def run_default_main ( cls, *args, **kwargs ):
      instance = cls ( *args, **kwargs )
      instance.setup()
      instance.default_main()
      return instance
   # --- end of run_default_main (...) ---

   def __init__ ( self, installed=True, stdout=None, stderr=None ):
      super ( IndependentRuntimeEnvironment, self ).__init__()

      if installed is None:
         installed_env = os.environ.get ( 'ROVERLAY_INSTALLED' )

         if installed_env:
            _installed = installed_env.lower() not in {
               '0', 'no', 'n', 'false',
            }
         else:
            _installed = False

      else:
         _installed = installed

      self.CONFIG_DEFAULTS = { 'installed': _installed, }
      self.PWD_INITIAL     = None

      self.config   = self.create_new_config()
      self.parser   = None
      self.options  = None
      self.commands = None
      self.prjroot  = None

      self.stdout   = stdout if stdout is not None else sys.stdout
      self.stderr   = stderr if stderr is not None else sys.stderr
      self._info    = self.stdout.write
      self._error   = self.stderr.write
      self.info     = self._info
      self.error    = self._error

      if _installed:
         self.INSTALLINFO = self.access_constant ( 'INSTALLINFO' )
      else:
         self.INSTALLINFO = None
   # --- end of __init__ (...) ---

   @roverlay.util.objects.abstractmethod
   def default_main ( self ):
      pass
   # --- end of default_main (...) ---

   def create_new_config ( self, config_str=None, apply_defaults=True ):
      ctree = roverlay.config.tree.ConfigTree ( register_static=False )

      if apply_defaults:
         ctree.merge_with ( self.CONFIG_DEFAULTS )

      if config_str:
         ctree.get_loader().parse_config ( config_str )

      return ctree
   # --- end of create_new_config (...) ---

   def reconfigure ( self, config_str=None ):
      self.reset_config()
      if config_str:
         self.config.get_loader().parse_config ( config_str )
   # --- end of reconfigure (...) ---

   def access_constant ( self, key ):
      return roverlay.config.const.lookup ( key )
   # --- end of access_constant (...) ---

   def wants_command ( self, *commands ):
      return any ( cmd in self.commands for cmd in commands )
   # --- end of wants_command (...) ---

   def extend_config ( self, additional_config ):
      self.config.merge_with ( additional_config )
   # --- end of extend_config (...) ---

   def reset_config ( self ):
      self.config.reset()
      self.extend_config ( self.CONFIG_DEFAULTS )
   # --- end of reset_config (...) ---

   def inject_config_path ( self, path, value ):
      return self.config.inject ( path, value, suppress_log=True )
   # --- end of inject_config_path (...) ---

   def locate_project_root ( self, ignore_missing=False ):
      prjroot = os.environ.get ( 'ROVERLAY_PRJROOT', None )

      couldbe_pydir = lambda a: (
         os.path.isdir ( a ) and os.path.isfile ( a + os.sep + '__init__.py' )
      )
      couldbe_prjroot = lambda b: couldbe_pydir ( b + os.sep + 'roverlay' )

      if prjroot:
         if not couldbe_prjroot ( prjroot ):
            self.error (
               'ROVERLAY_PRJROOT={p!r} does not seem to be correct - '
               'continuing.\n'.format ( p=prjroot )
            )
      else:
         if couldbe_prjroot ( self.PWD_INITIAL ):
            prjroot = self.PWD_INITIAL
         else:
            script_file = os.path.realpath ( sys.argv[0] )
            for root in roverlay.fsutil.walk_up (
               os.path.dirname ( script_file ), topdown=False, max_iter=7
            ):
               if couldbe_prjroot ( root ):
                  prjroot = root
                  break
               # -- end if
            else:
               msg = (
                  'cannot locate roverlay\'s project root - '
                  'please export ROVERLAY_PRJROOT=<dir>'
               )
               if ignore_missing:
                  self.error ( msg )
               else:
                  self.die ( msg )
            # -- end for
         # -- end if
      # -- end if not prjroot

      return prjroot
   # --- end of locate_project_root (...) ---

   @roverlay.util.objects.abstractmethod
   def create_argparser ( self ):
      pass
   # --- end of create_argparser (...) ---

   def setup_argparser ( self ):
      parser = self.create_argparser()
      if parser is not False:
         parser.setup()
         self.parser = parser

         parser.parse()

         self.options  = parser.get_options()
         self.commands = parser.get_commands()
   # --- end of do_setup_parser (...) ---

   def setup_common ( self, allow_prjroot_missing=True ):
      self.PWD_INITIAL = os.getcwd()
      if self.is_installed():
         self.prjroot = False
      else:
         self.prjroot = self.locate_project_root (
            ignore_missing=allow_prjroot_missing
         )

      roverlay.recipe.easylogger.force_console_logging (
         log_formatter = logging.Formatter ( self.LOG_FORMAT ),
         log_level     = (
            logging.DEBUG if self.LOG_LEVEL is None else self.LOG_LEVEL
         ),
      )
      self.setup_argparser()
   # --- end of setup_common (...) ---

   def setup ( self ):
      self.setup_common()
   # --- end of setup (...) ---

   def option ( self, key, fallback=None ):
      return self.options.get ( key, fallback )
   # --- end of option (...) ---

   def optionally ( self, func, key, *args, **kwargs ):
      if self.options.get ( key, False ):
         return func ( *args, **kwargs )
      else:
         return None
   # --- end of optionally (...) ---

   def is_installed ( self ):
      return self.config.get_or_fail ( 'installed' )
   # --- end of is_installed (...) ---

   installed = property ( is_installed )

# --- end of IndependentRuntimeEnvironment ---
