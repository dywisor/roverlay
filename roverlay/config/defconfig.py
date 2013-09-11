# R overlay -- config package, data for config file creation
# -*- coding: utf-8 -*-
# Copyright (C) 2013 André Erdmann <dywi@mailerd.de>
# Distributed under the terms of the GNU General Public License;
# either version 2 of the License, or (at your option) any later version.

# TODO: generate config file for not-installed versions

import os.path
import re
import textwrap

from .entryutil import deref_entry_safe, find_config_path

from . import entrymap
from . import tree


ENTRY_MAP = entrymap.CONFIG_ENTRY_MAP


EMPTY_STR = ""

RE_WS           = re.compile ( '\s+' )
COMMENT_WRAPPER = textwrap.TextWrapper (
   initial_indent='# ', subsequent_indent='#  ', width=70,
)

wrap_comment = lambda a: '\n'.join (
   COMMENT_WRAPPER.wrap ( RE_WS.sub ( ' ', str ( a ) ) )
)

listlike   = lambda b: (
   hasattr ( b, '__iter__' ) and not isinstance ( b, str )
)

do_iterate   = lambda c: c if listlike ( c ) else ( c, )
iter_lines   = lambda d: map ( str, do_iterate ( d ) )
wrap_comment_lines = lambda e: '\n'.join (
   map ( wrap_comment, do_iterate ( e ) )
)

class ConfigOptionMissing ( KeyError ):
   def __init__ ( self, key ):
      super ( ConfigOptionMissing, self ).__init__ (
         "{!r} has to be added first".format ( key )
      )

class ConfigValueError ( ValueError ):
   def __init__ ( self, key, value ):
      super ( ConfigValueError, self ).__init__ (
         "invalid value {!r} for option {!r}".format ( value, key )
      )

class ConfigOption ( object ):
   def __init__ ( self,
      name, default=None, required=None, recommended=False, description=None,
      use_default_desc=True, comment_default=False, append_newline=True,
      defaults_to=None
   ):
      self.name             = name
      self.map_entry        = deref_entry_safe ( name )
      self.default          = default
      self.required         = required or (
         not recommended if required is None else False
      )
      self.recommended      = recommended
      self.description      = description
      self.use_default_desc = use_default_desc
      self.comment_default  = comment_default
      self.append_newline   = append_newline
      self.value            = None
      self.defaults_to      = defaults_to
      self.comment_value    = False

      #self.is_set = False
   # --- end of __init__ (...) ---

   def set_value ( self, value ):
      self.value  = value
      #self.is_set = True

   def gen_str ( self ):
      entry = self.map_entry[1]

      if self.value is None:
         using_default = True
         self.value = self.default
#      elif self.value == self.default:
#         using_default = True
      else:
         using_default = False


      if using_default and self.comment_default:
         if self.required:
            yield wrap_comment ( "{} has to be set".format ( self.name ) )
         elif self.recommended:
            yield wrap_comment ( "{} should be set".format ( self.name ) )


      if self.use_default_desc:
         desc = entry.get ( 'description' ) or entry.get ( 'desc' )
         if desc:
            yield wrap_comment_lines ( desc )

      if self.description is True:
         yield wrap_comment ( self.name )
      elif self.description:
         yield wrap_comment_lines ( self.description )

      if self.defaults_to:
         if self.defaults_to is True:
            yield '#  Defaults to \"{}\".'.format ( self.default )
         elif listlike ( self.defaults_to ):
            yield '#  Defaults to \"{}\" ({}).'.format ( *self.defaults_to )
         else:
            yield '#  Defaults to \"{}\".'.format ( self.defaults_to )


      if self.comment_value or ( self.comment_default and using_default ):
         yield "#{k}=\"{v}\"".format ( k=self.name, v=self.value )
      else:
         yield "{k}=\"{v}\"".format ( k=self.name, v=self.value )

      if self.append_newline:
         yield EMPTY_STR
   # --- end of gen_str (...) ---

   def __str__ ( self ):
      return '\n'.join ( self.gen_str() )




def CommentedConfigOption (
   name, default=None, required=False,
   use_default_desc=False, append_newline=False, **kw
):
   return ConfigOption (
      name, default=default, comment_default=True, required=required,
      use_default_desc=use_default_desc, append_newline=append_newline, **kw
   )




class RoverlayConfigCreation ( object ):

   def __init__ ( self,
      work_root = '~/roverlay',
      data_root = '/usr/share/roverlay',
      conf_root = '/etc/roverlay',
   ):
      self.work_root = work_root
      self.data_root = data_root
      self.conf_root = conf_root

      self._ctree        = tree.ConfigTree()
      self._cloader      = self._ctree.get_loader()
      self._verify_value = self._cloader._make_and_verify_value

      self.reset()

   def get_workdir ( self, p ):
      return os.path.join ( self.work_root, p ).rstrip ( os.path.sep )

   def get_datadir ( self, p ):
      return os.path.join ( self.data_root, p ).rstrip ( os.path.sep )

   def get_confdir ( self, p ):
      return os.path.join ( self.conf_root, p ).rstrip ( os.path.sep )

   def iter_options ( self ):
      for item in self.config:
         if isinstance ( item, ConfigOption ):
            yield item

   def set_option ( self, key, value ):
      if key in self._cmap:
         option = self._cmap [key]

         if isinstance ( value, str ):
            if len ( value ) > 2 and value[1] == ',':
               v = value[0].lower()

               if v == 'w':
                  svalue = self.get_workdir ( value[2:] )
               elif v == 'd':
                  svalue = self.get_datadir ( value[2:] )
               elif v == 'c':
                  svalue = self.get_confdir ( value[2:] )
               else:
                  svalue = value
            else:
               svalue = value
         elif value:
            svalue = str ( value )
         else:
            svalue = None
         # -- end if, get value

         try:
            converted_value = self._verify_value (
               option.map_entry[1].get ( 'value_type' ), svalue
            )
         except ( TypeError, ValueError ):
            raise ConfigValueError ( key, value )

         if converted_value is not None:
            option.set_value ( svalue )
         elif isinstance ( value, str ) and not value:
            option.comment_value = True
         else:
            raise ConfigValueError ( key, value )
      else:
         raise ConfigOptionMissing ( key )

   def reset ( self ):
      workdir = self.get_workdir
      datadir = self.get_datadir
      confdir = self.get_confdir

      cachedir = lambda p=None: (
         workdir ( os.path.join ( 'cache', p ) if p else 'cache' )
      )


      self.config = [
         '# R-overlay.conf',
         '#  This is roverlay\'s main config file',
         '#',
         '',
         '# --- Required Configuration ---',
         '',
         ConfigOption ( 'DISTFILES',   workdir ( 'distfiles' ) ),
         ConfigOption ( 'OVERLAY_DIR', workdir ( 'overlay' ) ),
         ConfigOption ( 'DISTDIR',     workdir ( 'mirror' ) ),
         ConfigOption (
            'LOG_FILE', workdir ( 'log/roverlay.log' ), recommended=True,
            use_default_desc=False
         ),
         ConfigOption ( 'CACHEDIR', cachedir() ),
         ConfigOption (
            'PORTDIR', '/usr/portage', use_default_desc=False,
            description=(
               "portage directory",
               " used to scan for valid licenses",
            ),
         ),
         '',
         '# --- Logging Configuration (optional) ---',
         '',
         CommentedConfigOption ( 'LOG_LEVEL', 'WARNING',
            use_default_desc=True, append_newline=True,
         ),
         CommentedConfigOption ( 'LOG_LEVEL_CONSOLE', 'INFO' ),
         CommentedConfigOption ( 'LOG_LEVEL_FILE', 'ERROR' ),
         '',
         CommentedConfigOption ( 'LOG_FILE_ROTATE', 'yes',
            description='this enables per-run log files',
            append_newline=True, # defaults_to="no",
         ),
         CommentedConfigOption ( 'LOG_FILE_ROTATE_COUNT', '5',
            description='number of backup log files to keep',
            append_newline=True,
         ),
         '',
         '# --- Other Configuration Options ---',
         '',
         # ADDITIONS_DIR: confdir or workdir?
         ConfigOption ( 'ADDITIONS_DIR', confdir ( 'files' ), ),
         ConfigOption (
            'USE_EXPAND_RENAME', confdir ( 'files/use_expand.rename' ),
            comment_default=True, required=False,
         ),
         ConfigOption (
            'USE_EXPAND_DESC', confdir ( 'file/use_expand.desc' ),
            comment_default=True, required=False,
         ),
         ConfigOption (
            'SIMPLE_RULES_FILE', confdir ( 'simple-deprules.d' ),
            use_default_desc=True, recommended=True,
            description=(
               'using the default dependency rule files',
               'Can be extended by appending other directories/files'
            ),
         ),
         ConfigOption (
            'PACKAGE_RULES', confdir ( 'package-rules.d' ),
         ),
         ConfigOption (
            'STATS_DB', cachedir ( 'stats.rrd' ),
            defaults_to=( "", "disable persistent stats" ),
         ),
         ConfigOption (
            'STATS_INTERVAL', comment_default=True, required=False,
            default="14400", defaults_to=( "7200", "2 hours" ),
            description=(
               'expected time span between overlay creation runs, in seconds'
            ),
         ),
         ConfigOption (
            'EVENT_HOOK', datadir ( 'hooks/mux.sh' ),
         ),
         ConfigOption (
            'EVENT_HOOK_RC', confdir ( 'hookrc' ),
         ),
         ConfigOption (
            'EVENT_HOOK_RESTRICT', '-* db_written overlay_success user',
            description=(
               'Note:',
               ' setting -user is highly recommended when running roverlay as root',
            ),
            comment_default=False, required=False,
            defaults_to=( "*", "allow all" ),
         ),
         ConfigOption (
            'LICENSE_MAP', confdir ( 'license.map' )
         ),
         ConfigOption (
            'OVERLAY_ECLASS', datadir ( 'eclass/R-packages.eclass' ),
            use_default_desc=False, recommended=True,
            description=(
               'Not required but ebuilds won\'t be functional '
               'without the eclass'
            )
         ),
         ConfigOption (
            'OVERLAY_CATEGORY', 'sci-R', defaults_to=True,
            comment_default=True, required=False, use_default_desc=False,
            description="default category for created ebuilds",
         ),
         ConfigOption (
            'REPO_CONFIG', confdir ( 'repo.list' ),
            use_default_desc=False,
            description='using the default repo list'
         ),
         ConfigOption (
            'FIELD_DEFINITION', confdir ( 'description_fields.conf' ),
            use_default_desc=False,
            description='using the default field definition file',
         ),

         ConfigOption (
            'DISTDIR_STRATEGY', 'hardlink symlink',
            use_default_desc=False,
            description=(
               'using the default distdir strategy',
               ' try hard links first, then fall back to symbolic ones'
            ),
         ),
         CommentedConfigOption (
            'DISTDIR_VERIFY', 'no', use_default_desc=True,
            description=' usually not needed',
            append_newline=True,
         ),
         CommentedConfigOption (
            'DISTMAP_COMPRESSION', 'bzip2', use_default_desc=True,
            append_newline=True, defaults_to=True,
         ),
         CommentedConfigOption (
            'DISTMAP_FILE', '', use_default_desc=True, append_newline=True,
            defaults_to="<CACHEDIR>/distmap.db"
         ),
         ConfigOption (
            'USE_PORTAGE_LICENSES', 'no', required=False,
            comment_default=True, defaults_to="yes"
         ),
         ConfigOption (
            'CREATE_LICENSES_FILE', 'no', required=False,
            comment_default=True, defaults_to="yes"
         ),
         ConfigOption (
            'NOSYNC', 'yes', required=False, comment_default=True,
            defaults_to="no",
         ),
         ConfigOption (
            'MANIFEST_IMPLEMENTATION', "ebuild", required=False,
            use_default_desc=False, comment_default=True, defaults_to="next",
            description=(
               "Manifest file creation",
               ' Available choices are \'next\' (internal, fast)',
               ' and \'ebuild\' (using ebuild(1), slow, but failsafe).',
            ),
         ),
      ]

      self._cmap = {
         c.name: c for c in self.config if isinstance ( c, ConfigOption )
      }
   # --- end of reset (...) ---

   def gen_lines ( self ):
      for item in self.config:
         yield str ( item )
   # --- end of gen_lines (...) ---

   def get_lines ( self ):
      return list ( self.gen_lines() )
   # --- end of get_lines (...) ---

   def get_str ( self, append_newline=True ):
      ret = '\n'.join ( self.gen_lines() ).rstrip()
      return ( ret + '\n' ) if append_newline else ret
   # --- end of get_str (...) ---

   def __str__ ( self ):
      return self.get_str ( False )
   # --- end of __str__ (...) ---

# --- end of RoverlayConfigCreation ---
