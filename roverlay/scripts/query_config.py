# R overlay -- helper scripts package, query-config
# -*- coding: utf-8 -*-
# Copyright (C) 2014 André Erdmann <dywi@mailerd.de>
# Distributed under the terms of the GNU General Public License;
# either version 2 of the License, or (at your option) any later version.
#
#
# Script for querying roverlay's config / editing template files.
#
#  Usage:
#  * query-config -h
#
#  * query-config -l
#
#     Lists all known config options.
#     (Note: it's not possible to query all of these options)
#
#  * query-config [-C <config_file>] [-u] [-a|{option[=varname]}]
#
#     Prints roverlay's config options in shell usable format (without relying
#     on roverlay-sh). Prints all options if -a/--all is specified or no
#     option[=varname] is given. options can be renamed with "=varname".
#
#     Usage example:
#
#       $ eval $(query-config -C R-overlay.conf.tmp OVERLAY_DIR=OVERLAY OVERLAY_NAME)
#       $ echo $OVERLAY
#       $ echo $OVERLAY_NAME
#
#  * query-config [-C <config_file>] [-u] -f <infile> [-O <outfile>|-] {-v VAR[=VALUE]}
#
#     Replaces occurences of @@VARIABLES@@ in <infile> with values taken
#     from roverlay's config and writes the result to <outfile> or stdout.
#     (variables may also be specified with -v VAR=VALUE, which take precedence
#     over roverlay's config, e.g. "-v SERVER_NAME=roverlay").
#
#     Usage example:
#
#       $ query-config -C ~roverlay_user/roverlay/R-overlay.conf \
#          -f nginx.conf.in -O nginx.conf -v SERVER_ADDR=... -v SERVER_NAME=...
#
#     A non-zero exit code indicates that one or more variables could not be
#     replaced.
#
#
from __future__ import print_function, unicode_literals

import argparse
import logging
import re
import os
import sys

import roverlay.core
import roverlay.strutil
from roverlay.config.entryutil import iter_config_keys

__all__ = [ 'query_config_main', ]


EX_OK    = os.EX_OK
EX_ERR   = os.EX_OK^1
EX_MISS  = os.EX_OK^2
EX_IRUPT = os.EX_OK^130

RE_VAR_REF = re.compile ( "@@([a-zA-Z_]+)@@" )
RE_VARNAME = re.compile ( "^[a-zA-Z_]+$" )


class VarnameArgumentError ( argparse.ArgumentTypeError ):
   def __init__ ( self, name ):
      super ( VarnameArgumentError, self ).__init__ (
         "invalid variable name: {!r}".format ( name )
      )
# --- end of VarnameArgumentError ---

def get_value_str ( value, list_join_seq=" " ):
   if value is None:
      return ""
   elif hasattr ( value, '__iter__' ) and not isinstance ( value, str ):
      return list_join_seq.join ( map ( str, value ) )
   elif isinstance ( value, bool ):
      return "1" if value else "0"
   else:
      return str ( value )
# --- end of get_value_str (...) ---

def format_variables ( vardict, append_newline=True ):
   retstr = "\n".join (
      "{varname!s}=\"{value!s}\"".format ( varname=k, value=v )
         for k, v in sorted ( vardict.items(), key=lambda kv: kv[0] )
   )
   return ( retstr + "\n" ) if append_newline else retstr
# --- end of format_variables (...) ---

def get_parser():
   def arg_couldbe_file ( value ):
      if value is None or value == '-':
         return value
      elif value:
         f = os.path.abspath ( value )
         if not os.path.exists ( f ) or not os.path.isdir ( f ):
            return f
      raise argparse.ArgumentTypeError (
         "{!r} cannot be a file.".format ( value )
      )
   # --- end of arg_couldbe_file (...) ---

   def arg_is_filepath_or_none ( value ):
      if value:
         f = os.path.abspath ( value )
         if os.path.isfile ( f ):
            return f
      elif value is None:
         return value
      raise argparse.ArgumentTypeError (
         "{!r} is not a file.".format ( value )
      )
   # --- end of arg_is_filepath_or_none (...) ---

   def arg_is_varname ( value ):
      if value:
         vname, sepa, valias = value.partition ( '=' )
         if not RE_VARNAME.match ( vname ):
            raise VarnameArgumentError ( vname )
         elif sepa:
            if not RE_VARNAME.match ( valias ):
               raise VarnameArgumentError ( valias )
            else:
               return ( vname, valias )
         else:
            return vname
            #return ( vname, vname )
      else:
         return None
   # --- end of arg_is_varname (...) ---

   def arg_is_variable ( value ):
      if value:
         key, sepa, value = value.partition ( "=" )
         if sepa:
            return ( key, roverlay.strutil.unquote ( value ) )
         else:
            return ( key, "" )
      raise argparse.ArgumentTypeError ( value )
   # --- end of arg_is_variable (...) ---

   parser = argparse.ArgumentParser (
      description = (
         "query config options and output them in shell-usable format"
      ),
      epilog = (
         'Exit codes:\n'
         '* {EX_OK}: success\n'
         '* {EX_ERR}: unspecified error, e.g. invalid config entry map\n'
         '* {EX_MISS}: one or more config keys could not be found\n'
      ).format ( EX_OK=EX_OK, EX_MISS=EX_MISS, EX_ERR=EX_ERR ),
      formatter_class = argparse.RawDescriptionHelpFormatter
   )

   parser.add_argument (
      "config_keys", metavar="<config_key>", type=arg_is_varname, nargs="*",
      help="config key (or <config_key>=<alias_key>)"
   )

   parser.add_argument (
      "-C", "--config-file", metavar="<file>", default=None,
      type=arg_is_filepath_or_none,
      help="path to the config file",
   )

   parser.add_argument (
      "-a", "--all", dest="print_all", default=False, action="store_true",
      help="print all options"
   )

   parser.add_argument (
      "-l", "--list-all", dest="list_all", default=False, action="store_true",
      help="instead of printing options: list all keys"
   )

   parser.add_argument (
      "-u", "--empty-missing", default=False, action="store_true",
      help="set missing variables to the empty string"
   )

   parser.add_argument (
      "-f", "--from-file", metavar="<file>", default=None,
      type=arg_is_filepath_or_none,
      help="read config keys from <file>"
   )

   parser.add_argument (
      "-O", "--outfile", metavar="<file>", default=None,
      type=arg_couldbe_file,
      help=(
         'in conjunction with --from-file: replace variable references and '
         'write the resulting text to <file>'
      )
   )

   parser.add_argument (
      "-v", "--variable", metavar="<key=\"value\">", dest="extra_vars",
      default=[], action="append", type=arg_is_variable,
      help="additional variables (only with --outfile)"
   )

   return parser
# --- end of get_parser (...) ---

def get_all_config_keys():
   return [ k.upper() for k in iter_config_keys() ]
# --- end of get_all_config_keys (...) ---

def get_vardict ( config, argv, keys ):
   return config.query_by_name (
      keys, empty_missing=argv.empty_missing, convert_value=get_value_str
   )
# --- end of get_vardict (...) ---

def main__print_variables ( config, argv, stream, config_keys ):
   num_missing, cvars = get_vardict ( config, argv, config_keys )
   if cvars:
      stream.write ( format_variables ( cvars ) )
   return num_missing
# --- end of main__print_variables (...) ---

def query_config_main ( is_installed ):
   parser = get_parser()
   argv   = parser.parse_args()
   stream = sys.stdout

   # setup
   ## logging
   roverlay.core.force_console_logging ( log_level=logging.WARNING )

   ## main config
   if argv.config_file is None:
      config_file = roverlay.core.locate_config_file ( is_installed )
   else:
      config_file = argv.config_file

   # passing installed=True|False doesn't really matter
   config = roverlay.core.load_config_file (
      config_file, extraconf={ 'installed': is_installed, },
      setup_logger=False, load_main_only=True
   )

   # perform actions as requested

   # --list-all: print all config keys and exit
   if argv.list_all:
      stream.write ( "\n".join ( sorted ( get_all_config_keys() ) ) + "\n" )
      return EX_OK

   # --all or no config keys specified: print all config options as variables
   elif argv.print_all or not any (( argv.from_file, argv.config_keys, )):
      main__print_variables ( config, argv, stream, get_all_config_keys() )
      # don't return EX_MISS if --all was specified
      return EX_OK

   # --from-file with --outfile:
   #   replace @@VARIABLES@@ in file and write to --outfile (or stdout)
   elif argv.from_file and argv.outfile:
      # COULDFIX: exit code when --variable is used
      #
      # (a) get_vardict(): return a list of missing vars and compare it
      #                    to the final cvars
      # (b) check the resulting str for missing vars (RE_VAR_REF.search)
      #
      #  Using (b) for now (and unconditionally, so that the output
      #  always gets verified).
      #

      # list of 2-tuples ( line, set<varnames> )
      input_lines = list()
      config_keys = set()
      with open ( argv.from_file, 'rt' ) as FH:
         for line in FH.readlines():
            varnames = set ( RE_VAR_REF.findall ( line ) )
            input_lines.append ( ( line, varnames ) )
            config_keys |= varnames
         # -- end for
      # -- end with

      num_missing, cvars = get_vardict ( config, argv, config_keys )
      del num_missing

      if argv.extra_vars:
         for k, v in argv.extra_vars:
            cvars[k] = v
      # -- end if extra vars

      # create a dict<varname => (regex for replacing varname,replacement)>
      #  where (re_object,replacement) := (re<@@varname@@>,value)
      re_repl = {
         k : ( re.compile ( "@@" + k + "@@" ), v ) for k, v in cvars.items()
      }

      # iterate through input_lines a second time, replacing @@VARNAMES@@
      # (COULDFIX: could be done in one loop // create cvars on-the-fly (defaultdict etc))
      output_lines = []
      vars_missing = set()
      for line, varnames in input_lines:
         # apply replace operations as needed
         for varname in varnames:
            try:
               re_obj, repl = re_repl [varname]
            except KeyError:
               # cannot replace varname
               vars_missing.add ( varname )
            else:
               line = re_obj.sub ( repl, line )
         # -- end for <varname // replace>

         output_lines.append ( line )
      # -- end for <input_lines>

      # write output_lines
      if argv.outfile == '-':
         stream.write ( ''.join ( output_lines ) )
      else:
         with open ( argv.outfile, 'wt' ) as FH:
            FH.write ( ''.join ( output_lines ) )
      # -- end write output_lines

      return EX_MISS if vars_missing else EX_OK

   # --from-file (without --outfile): read config keys from file
   elif argv.from_file:
      config_keys = set()
      with open ( argv.from_file, 'rt' ) as FH:
         for line in FH.readlines():
            config_keys.update ( RE_VAR_REF.findall ( line ) )
      # -- end with

      if main__print_variables ( config, argv, stream, config_keys ):
         return EX_MISS
      else:
         return EX_OK

   # else filter out False/None values
   elif main__print_variables (
      config, argv, stream, [ kx for kx in argv.config_keys if kx ]
   ):
      return EX_MISS
   else:
      return EX_OK

# --- end of query_config_main (...) ---
