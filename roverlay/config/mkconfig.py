# R overlay -- config package, config file creation
# -*- coding: utf-8 -*-
# Copyright (C) 2013 André Erdmann <dywi@mailerd.de>
# Distributed under the terms of the GNU General Public License;
# either version 2 of the License, or (at your option) any later version.

import sys

from roverlay.config.entryutil import deref_entry_safe
from roverlay.config.defconfig import RoverlayConfigCreation

import roverlay.argutil
import roverlay.argparser

class MkConfigArgParser ( roverlay.argparser.RoverlayArgumentParserBase ):

   DESCRIPTION_TEMPLATE = 'create roverlay config file'

   SETUP_TARGETS = ( 'mkconfig', )

   def setup_mkconfig ( self ):
      arg = self.setup_setup_minimal()

      arg (
         '--output', '-O', metavar="<file>",
         default='-',
         type=roverlay.argutil.couldbe_stdout_or_file,
         help='output file/stream for config (use \'-\' for stdout)',
      )

      arg (
         'variables', nargs="*", metavar='<option>=\"<value>\"',
         type=roverlay.argutil.is_config_opt,
         help='additional config variables',
      )
   # --- end of setup_mkconfig (...) ---

# --- end of MkConfigArgParser ---


def make_config():
   parser = MkConfigArgParser()
   parser.setup()
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
