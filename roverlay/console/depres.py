# R overlay --
# -*- coding: utf-8 -*-
# Copyright (C) 2013 André Erdmann <dywi@mailerd.de>
# Distributed under the terms of the GNU General Public License;
# either version 2 of the License, or (at your option) any later version.

import sys

import roverlay.console.base
import roverlay.console.interpreter

# hidden import
#import roverlay.interface.depres

# TODO/FIXME: turn off dep resolver logging: "RESOLVED: this as that"

class DepresConsoleInterpreter (
   roverlay.console.interpreter.ConsoleInterpreter
):
   def __init__ ( self, *args, **kwargs ):
      super ( DepresConsoleInterpreter, self ).__init__ ( *args, **kwargs )
      self.intro = "depres console (r2)"

   def setup_aliases ( self ):
      self.add_alias ( "help", "h" )

      # rule pool management
      self.add_alias ( "add_pool", "<<" )
      self.add_alias ( "unwind_pool", ">>" )
      self.add_alias ( "print_pool", "p" )

      # rule creation
      self.add_alias ( "add_rule", "+" )
      self.add_alias ( "load_conf", "lc" )

      # dep res
      self.add_alias ( "resolve", "??" )
   # --- end of setup_aliases (...) ---


   def reset ( self, soft=True ):
      super ( DepresConsoleInterpreter, self ).reset ( soft=soft )
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
      if line:
         ret = self.interface.resolve ( line )
         if ret is None:
            sys.stdout.write ( "{!r} could not be resolved.\n".format ( line ) )
         elif not ret:
            sys.stdout.write (
               "{!r} has been resolved as nothing(?)\n".format ( line )
            )
         elif len ( ret ) == 1:
            sys.stdout.write (
               "{!r} has been resolved as {}.\n".format (
                  line, (
                     ret[0].dep if ( ret[0] and ret[0].dep is not None )
                     else "<ignored>"
                  )
               )
            )
         else:
            sys.stdout.write (
               "{!r} has been resolved as {}.\n".format (
                  line, ( ', '.join ( str ( dep ) for dep in ret ) )
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
      """Removes the topmost rule pool."""
      if self.interface.discard_pool():
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
      """Prints the topmost pool (TODO:: or all)."""
      sys.stdout.write ( self.interface.visualize_pool() )
      sys.stdout.write ( "\n" )
   # --- end of do_print_pool (...) ---

   def do_print ( self, line ):
      """Prints the topmost pool (TODO:: or all)."""
      return self.do_print_pool ( line )
   # --- end of do_print (...) ---

   def do_load_conf ( self, line ):
      """Load configured dependency rule files."""
      self.interface.discard_empty_pools()
      if not self.interface.load_rules_from_config ( ignore_missing=True ):
         sys.stderr.write ( "failed to load rule files!\n" )

   # --- end of do_load_conf (...) ---



class DepresConsole ( roverlay.console.base.MainConsole ):
   INTERPRETER_CLS = DepresConsoleInterpreter

   def get_interface ( self ):
      return self.root_interface.spawn_interface ( "depres" )
