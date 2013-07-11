# R overlay -- config package, config file creation
# -*- coding: utf-8 -*-
# Copyright (C) 2013 André Erdmann <dywi@mailerd.de>
# Distributed under the terms of the GNU General Public License;
# either version 2 of the License, or (at your option) any later version.

import sys
import os.path
import argparse

from .entryutil import deref_entry_safe
from .defconfig import RoverlayConfigCreation

def get_parser():
   def couldbe_fs_file ( value ):
      if value:
         f = os.path.abspath ( value )
         if not os.path.exists ( f ) or os.path.isfile ( f ):
            return f

      raise argparse.ArgumentTypeError (
         "{!r} is not a file.".format ( value )
      )

   def couldbe_stdout_or_file ( value ):
      return value if value == "-" else couldbe_fs_file ( value )

   def dirstr ( value ):
      if value:
         if value[0] == '~':
            return value.rstrip ( os.path.sep )
         else:
            return os.path.sep + value.strip ( os.path.sep )
      else:
         raise argparse.ArgumentTypeError (
            "cannot create dir-string for {!r}".format ( value )
         )

   def is_config_opt ( value ):
      try:
         k = value.partition ( '=' ) [0]
         map_entry = deref_entry_safe ( k )
      except KeyError:
         raise argparse.ArgumentTypeError (
            "no such config option: {!r}".format ( k )
         )
      else:
         return value


   parser = argparse.ArgumentParser (
      description='create roverlay config file',
      add_help=True,
      formatter_class=argparse.RawDescriptionHelpFormatter,
   )

   arg = parser.add_argument

   arg (
      'variables', nargs="*", metavar='<option>=\"<value>\"', type=is_config_opt,
      help='config variables to set',
   )
   arg (
      '--output', '-O', metavar="<file>",
      default='-', type=couldbe_stdout_or_file,
      help='output file/stream for config (use \'-\' for stdout)',
   )
   arg (
      '--work-root', '-W', metavar="<dir>",
      default="~/roverlay", type=dirstr,
      help='root directory for variable data (distfiles, overlay,...)',
   )
   arg (
      '--data-root', '-D', metavar="<dir>",
      default="/usr/share/roverlay", type=dirstr,
      help='root directory for static data (eclass, hook scripts,...)',
   )
   arg (
      '--conf-root', '-C', metavar="<dir>",
      default="/etc/roverlay", type=dirstr,
      help='root directory for config files (dependency rules,...)',
   )

   return parser
# --- end of get_parser (...) ---

def make_config():
   parser       = get_parser()
   arg_config   = parser.parse_args()
   conf_creator = RoverlayConfigCreation (
      work_root=arg_config.work_root, data_root=arg_config.data_root,
      conf_root=arg_config.conf_root
   )

   for kv in arg_config.variables:
      key, sepa, value = kv.partition ( '=' )
      if not sepa:
         raise Exception ( "bad variable given: {!r}".format ( kv ) )
      else:
         conf_creator.set_option ( key, value )


   config_str = str ( conf_creator ).rstrip() + '\n'

   if arg_config.output == '-':
      sys.stdout.write ( config_str )
   else:
      with open ( arg_config.output, 'wt' ) as FH:
         FH.write ( config_str )
