# R overlay --
# -*- coding: utf-8 -*-
# Copyright (C) 2013 André Erdmann <dywi@mailerd.de>
# Distributed under the terms of the GNU General Public License;
# either version 2 of the License, or (at your option) any later version.

import sys

import roverlay.interface.main
import roverlay.console.interpreter

class RoverlayConsole ( object ):
   pass

class MainConsole ( RoverlayConsole ):

   INTERPRETER_CLS = roverlay.console.interpreter.ConsoleInterpreter

   def __init__ ( self, config_file=None ):
      super ( MainConsole, self ).__init__()
      self.config         = None
      self.root_interface = roverlay.interface.main.MainInterface()
      self.interpreter    = self.INTERPRETER_CLS()
      self.interface      = None

      if config_file is not None:
         self.setup ( config_file )
   # --- end of __init__ (...) ---

   def get_interface ( self ):
      return self.root_interface

   def has_config ( self ):
      return self.config is not None
   # --- end of has_config (...) ---

   def setup ( self, config_file ):
      self.root_interface.setup ( config_file )

      self.config    = self.root_interface.config
      self.interface = self.get_interface()

      self.interpreter.setup ( self.interface )
   # --- end of setup (...) ---

   def run ( self ):
      self.interpreter.cmdloop()
   # --- end of run (...) ---

   def _want_resume ( self ):
      if self.interpreter.state.is_paused():
         return False
      elif self.interpreter.state == self.interpreter.state.STATE_QUIT:
         return False
      else:
         return True
   # --- end of _want_resume (...) ---

   def run_forever ( self ):
      retry = True
      while retry:
         retry = False
         try:
            self.run()
         except roverlay.console.interpreter.ConsoleException as ce:
            sys.stderr.write (
               "{}: {}\n".format ( ce.__class__.__name__, str ( ce ) )
            )
            retry = self._want_resume()
         except KeyboardInterrupt:
            sys.stdout.write ( '\n^C\n' )
            retry = self._want_resume()
   # --- end of run_forever (...) ---

# --- end of MainConsole ---
