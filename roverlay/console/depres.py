# R overlay --
# -*- coding: utf-8 -*-
# Copyright (C) 2013 André Erdmann <dywi@mailerd.de>
# Distributed under the terms of the GNU General Public License;
# either version 2 of the License, or (at your option) any later version.

import os
import sys

import roverlay.console.base
import roverlay.console.interpreter
from roverlay.console.interpreter import ConsoleInterpreter

import roverlay.strutil
from roverlay.strutil import unquote, unquote_all

#wrap_lastarg = roverlay.console.interpreter.wrap_lastarg

# hidden import
#import roverlay.interface.depres

# TODO/FIXME: turn off dep resolver logging: "RESOLVED: this as that"

class DepresConsoleInterpreter ( ConsoleInterpreter ):
   # Note: this is an old-style class (inherited from cmd.Cmd)

   CHROOT_ALLOWED = frozenset ({ 'resolve', })
   COMP_CHROOT_ALLOWED = list ( CHROOT_ALLOWED | { '/', } )

   def __init__ ( self, *args, **kwargs ):
      ConsoleInterpreter.__init__ ( self, *args, **kwargs )
      self.intro = (
         '== dependency resolution console (r2) ==\n'
         'Run \'help\' to list all known commands.\n'
         'More specifically, \'help <cmd>\' prints a help message for the '
         'given command, and \'help --list\' lists all help topics.\n'
         'Use \'load_conf\' or \'lc\' to load the configured rule files.\n'
      )

   def setup_aliases ( self ):
      ConsoleInterpreter.setup_aliases ( self )

      self.add_alias ( "help", "h" )

      # rule pool management
      self.add_alias ( "add_pool", "<<" )
      self.add_alias ( "unwind_pool", ">>" )
      self.add_alias ( "print_pool", "p" )

      # rule creation
      self.add_alias ( "add_rule", "+" )

      # load rules
      self.add_alias ( "load_conf", "lc" )
      self.add_alias ( "load", "l" )

      # rule export
      self.add_alias ( "write", "w" )

      # depres
      self.add_alias ( "resolve", "??" )

      # enter/leave depres chroot
      self.add_alias ( "chroot /resolve", "!" )
      self.add_alias ( "chroot /", "!!" )
   # --- end of setup_aliases (...) ---

   def setup_argparser ( self ):
      ConsoleInterpreter.setup_argparser ( self )

      # write
      parser = self.get_argparser ( "write", create=True )

      parser.add_argument ( 'outfile', nargs=1, metavar="<file>", type=str,
         help="file to write"
      )
      parser.add_opt_in ( '--force', '-f', help='overwrite existing files' )
      parser.add_opt_in ( '--all', '-a',
         help="write all pools into a single file"
      )

      # load
      parser = self.get_argparser ( "load", create=True )

      parser.add_argument ( 'files', nargs='*', metavar="<file|dir>",
         type=self.argparse_fspath, help="files/dirs to load",
      )

      # print_pool
      parser = self.get_argparser ( "print_pool", create=True )

      parser.add_opt_in ( '--all', '-a', help="print all pools" )
      parser.add_argument ( 'pools', metavar='<id>', nargs='*',
         help="print specific pools (by id)", type=int,
      )


      # unwind_pool
      parser = self.get_argparser ( "unwind_pool", create=True )

      parser.add_opt_in ( '--all', '-a', help='discard all rule pools' )

   # --- end of setup_argparser (...) ---

   def reset ( self, soft=True ):
      ConsoleInterpreter.reset ( self, soft=soft )
      if not soft:
         self.interface.discard_pools()

   def do_resolve ( self, line ):
      """Resolve a dependency string.

      Usage:
      * resolve <dependency string>
      * ?? <dependency string>

      Examples:
      * resolve R
      * resolve fftw 3.2
      """
      depstr = unquote ( line )
      if depstr:
         ret = self.interface.resolve ( depstr )
         if ret is None:
            sys.stdout.write (
               "{!r} could not be resolved.\n".format ( depstr )
            )
         elif not ret:
            sys.stdout.write (
               "{!r} has been resolved as nothing(?)\n".format ( depstr )
            )
         elif len ( ret ) == 1:
            sys.stdout.write (
               "{!r} has been resolved as {}.\n".format (
                  depstr, (
                     ret[0].dep if ( ret[0] and ret[0].dep is not None )
                     else "<ignored>"
                  )
               )
            )
         else:
            sys.stdout.write (
               "{!r} has been resolved as {}.\n".format (
                  depstr, ( ', '.join ( str ( dep ) for dep in ret ) )
               )
            )
      else:
         sys.stderr.write ( "Usage: resolve <dependency string>\n" )
   # --- end of do_resolve (...) ---

   def do_add_pool ( self, line ):
      """Creates a new rule pool on top of the existing ones."""
      self.interface.get_new_pool()
   # --- end of do_add_pool (...) ---

   def do_unwind_pool ( self, line ):
      """Removes the topmost rule pool. See --help for usage."""
      args = self.parse_cmdline ( "unwind_pool", line )

      if args is None:
         pass
      elif args.all:
         count = self.interface.discard_all_pools()
         if count == 0:
            sys.stdout.write ( "resolver has no pools.\n" )
         else:
            sys.stdout.write (
               "{:d} pools have been removed.\n".format ( count )
            )
      elif self.interface.discard_pool():
         sys.stdout.write ( "pool has been removed.\n" )
      else:
         sys.stdout.write ( "resolver has no pools.\n" )
   # --- end of do_unwind_pool (...) ---

   def do_add_rule ( self, line ):
      """Adds a rule. Rules have to be given in rule file syntax.

      Usage:
      * add_rule <str>
      * + <str>

      Examples:
      * add_rule dev-lang/R :: R
      """
      if self._cmdbuffer:
         self.interface.add_rule_list ( self.get_argbuffer() )
      elif line:
         self.interface.add_rule ( line )
      else:
         self.warn_usage()

      # compile rules if not inside of a rule
      self.interface.try_compile_rules()
   # --- end of do_add_rule (...) ---

   def do_print_pool ( self, line ):
      """Prints the topmost pool. See --help for usage."""
      args = self.parse_cmdline ( "print_pool", line )
      if args is not None:
         if args.all:
            sys.stdout.write ( self.interface.visualize_pools() )
         elif args.pools:
            sys.stdout.write ( self.interface.visualize_pools ( args.pools ) )
         else:
            sys.stdout.write ( self.interface.visualize_pool() )

         sys.stdout.write ( "\n" )
   # --- end of do_print_pool (...) ---

   def do_print ( self, line ):
      """Prints the topmost pool. See --help for usage."""
      return self.do_print_pool ( line )
   # --- end of do_print (...) ---

   def do_load_conf ( self, line ):
      """Load configured dependency rule files. See --help for usage."""
      self.interface.discard_empty_pools()
      if not self.interface.load_rules_from_config ( ignore_missing=True ):
         sys.stderr.write ( "failed to load rule files!\n" )
   # --- end of do_load_conf (...) ---

   def complete_load ( self, *args, **kw ):
      return self.complete_fspath ( *args, **kw )
   # --- end of complete_load (...) ---

   def do_load ( self, line ):
      """Loads a dependency rule file.

      Usage: load <file|dir>

      See --help for detailed usage.
      """
      self.interface.discard_empty_pools()

      args = self.parse_cmdline ( "load", line )
      if args and args.files:
         if not self.interface.load_rule_files (
            args.files, ignore_missing=True
         ):
            sys.stderr.write (
               "failed to load rule file {!r}\n".format ( line )
            )
   # --- end of do_load (...) ---

   def complete_write ( self, text, *args, **kw ):
      return self.complete_fspath ( text, *args, **kw )
   # --- end of complete_write (...) ---

   def do_write ( self, line ):
      """Exports the rules of the topmost rule pool into a file.
      See --help for usage."""

      args = self.parse_cmdline ( "write", line )
      if args and args.outfile and args.outfile[0]:
         outfile = self.get_fspath ( args.outfile[0] )
         if args.force or not os.path.exists ( outfile ):
            try:
               output = (
                  self.interface.visualize_pools() if args.all
                     else self.interface.visualize_pool()
               )
               with open ( outfile, 'wt' ) as FH:
                  FH.write ( output )
                  FH.write ( '\n' )
            except Exception as err:
               sys.stderr.write ( "write failed: {}\n".format ( err ) )
            else:
               self.set_lastarg ( outfile )
               sys.stdout.write ( "wrote {!r}\n".format ( outfile ) )
         else:
            sys.stderr.write ( "cannot write {!r}: exists\n".format ( outfile ) )
      else:
         sys.stderr.write ( "nothing written!\n" )
   # --- end of do_write (...) ---

# --- end of DepresConsoleInterpreter ---

class DepresConsole ( roverlay.console.base.MainConsole ):
   INTERPRETER_CLS = DepresConsoleInterpreter

   def get_interface ( self ):
      return self.root_interface.spawn_interface ( "depres" )
   # --- end of get_interface (...) ---

# --- end of DepresConsole ---
