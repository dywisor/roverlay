# R overlay -- runtime env
# -*- coding: utf-8 -*-
# Copyright (C) 2013 André Erdmann <dywi@mailerd.de>
# Distributed under the terms of the GNU General Public License;
# either version 2 of the License, or (at your option) any later version.

import logging
import errno
import sys


import roverlay.argparser
import roverlay.core
import roverlay.hook
import roverlay.remote.repolist
import roverlay.stats.collector
import roverlay.util.objects
import roverlay.recipe.easylogger

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

   ARG_PARSER_CLS = roverlay.argparser.RoverlayMainArgumentParser

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
                  'rrdtool not available. '
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

   def __init__ ( self, installed=True, stdout=None, stderr=None ):
      super ( IndependentRuntimeEnvironment, self ).__init__()

      self.CONFIG_DEFAULTS = { 'installed': installed, }

      self.config   = self.create_new_config()
      self.parser   = None
      self.options  = None
      self.commands = None

      self.stdout   = stdout if stdout is not None else sys.stdout
      self.stderr   = stderr if stderr is not None else sys.stderr
      self._info    = self.stdout.write
      self._error   = self.stderr.write
      self.info     = self._info
      self.error    = self._error

      if installed:
         self.INSTALLINFO = self.access_constant ( 'INSTALLINFO' )
      else:
         self.INSTALLINFO = None
   # --- end of __init__ (...) ---

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

   def setup_common ( self ):
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
