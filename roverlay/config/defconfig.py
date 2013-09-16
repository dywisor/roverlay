# R overlay -- config package, data for config file creation
# -*- coding: utf-8 -*-
# Copyright (C) 2013 André Erdmann <dywi@mailerd.de>
# Distributed under the terms of the GNU General Public License;
# either version 2 of the License, or (at your option) any later version.

import os.path
import re
import textwrap

from .entryutil import deref_entry_safe

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

def _fspath_prefix_func ( *prefix ):
   _PREFIX = os.path.join ( *prefix )
   def wrapped ( *p ):
      if p:
         return os.path.join ( _PREFIX, *p ).rstrip ( os.path.sep )
      else:
         return _PREFIX
   # --- end of wrapped (...) ---

   return wrapped
# --- end of _fspath_prefix_func (...) ---


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
   # --- end of __str__ (...) ---

# --- end of ConfigOption ---


class RoverlayConfigCreation ( object ):

   def __init__ ( self,
      is_installed,
      work_root     = '~/roverlay',
      data_root     = '/usr/share/roverlay',
      conf_root     = '/etc/roverlay',
      additions_dir = '/etc/roverlay/files',
   ):
      self.work_root         = work_root
      self.data_root         = data_root
      self.conf_root         = conf_root
      self.additions_dir     = additions_dir

      self.get_workdir       = _fspath_prefix_func ( self.work_root )
      self.get_datadir       = _fspath_prefix_func ( self.data_root )
      self.get_confdir       = _fspath_prefix_func ( self.conf_root )
      self.get_additions_dir = _fspath_prefix_func ( self.additions_dir )

      self._ctree            = tree.ConfigTree()
      self._cloader          = self._ctree.get_loader()
      self._verify_value     = self._cloader._make_and_verify_value
      self.reset ( is_installed=is_installed )
   # --- end of __init__ (...) ---

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

   def reset ( self, is_installed ):
      workdir       = self.get_workdir
      datadir       = self.get_datadir
      confdir       = self.get_confdir
      additions_dir = self.get_additions_dir

      cachedir = _fspath_prefix_func ( self.work_root, 'cache' )


      UNLESS_INSTALLED = lambda *a, **b: (
         None if is_installed else ConfigOption ( *a, **b )
      )
      IF_INSTALLED = lambda *a, **b: (
         ConfigOption ( *a, **b ) if is_installed else None
      )
      get_val = lambda v_inst, v_standalone: (
         v_inst if is_installed else v_standalone
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
         ConfigOption (
            'LOG_LEVEL', get_val ( 'WARNING', 'INFO' ), required=False,
            comment_default=is_installed,
         ),
         ConfigOption (
            'LOG_LEVEL_CONSOLE', get_val ( 'INFO', 'WARNING' ),
            required=False, comment_default=is_installed,
            use_default_desc=False, append_newline=False,
         ),
         ConfigOption (
            'LOG_LEVEL_FILE', get_val ( 'ERROR', 'WARNING' ),
            required=False, comment_default=is_installed,
            use_default_desc=False, append_newline=False,
         ),
         '',
         ConfigOption (
            'LOG_FILE_ROTATE', 'yes', required=False,
            comment_default=is_installed, use_default_desc=False,
            description='this enables per-run log files',
            # defaults_to="no"
         ),
         ConfigOption (
            'LOG_FILE_ROTATE_COUNT', '5', required=False,
            comment_default=True, use_default_desc=False,
            description='number of backup log files to keep',
            defaults_to="3"
         ),
         ConfigOption (
            'LOG_FILE_UNRESOLVABLE',
            workdir ( 'log', 'dep_unresolvable.log' ), required=False,
            comment_default=is_installed,
         ),
         '',
         '# --- Other Configuration Options ---',
         '',
         # ADDITIONS_DIR: confdir or workdir?
         ConfigOption ( 'ADDITIONS_DIR', additions_dir() ),
         ConfigOption (
            'USE_EXPAND_RENAME', additions_dir ( 'use_expand.rename' ),
            comment_default=True, required=False,
         ),
         ConfigOption (
            'USE_EXPAND_DESC', additions_dir ( 'use_expand.desc' ),
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
            'PACKAGE_RULES', confdir ( 'package_rules' ),
         ),
         ConfigOption (
            'STATS_DB', cachedir ( 'stats.db' ),
            defaults_to=( "", "disable persistent stats" ),
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
         UNLESS_INSTALLED ( 'TEMPLATE_ROOT', datadir ( 'mako_templates' ) ),
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
         UNLESS_INSTALLED (
            'DESCRIPTION_DIR', cachedir ( 'desc-files' ),
            comment_default=True, required=False,
            description='Note that this slows overlay creation down.',
         ),
         ConfigOption (
            'DISTDIR_STRATEGY', 'hardlink symlink',
            use_default_desc=False,
            description=(
               'using the default distdir strategy',
               ' try hard links first, then fall back to symbolic ones'
            ),
         ),
         ConfigOption (
            'DISTDIR_VERIFY', 'no', required=False, comment_default=True,
            description=' usually not needed',
         ),
         ConfigOption (
            'DISTMAP_COMPRESSION', 'bzip2', required=False,
            comment_default=True, defaults_to=True,
         ),
         ConfigOption (
            'DISTMAP_FILE', '', required=False, comment_default=True,
            defaults_to="<CACHEDIR>/distmap.db",
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
         if item is not None:
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
