# R overlay --
# -*- coding: utf-8 -*-
# Copyright (C) 2013 André Erdmann <dywi@mailerd.de>
# Distributed under the terms of the GNU General Public License;
# either version 2 of the License, or (at your option) any later version.

import collections
import sys
import cmd

def fcopy ( func, name=None, mark_as_alias=True ):
   """Creates an alias to func."""
   def wrapped ( *args, **kwargs ):
      return func ( *args, **kwargs )

   wrapped.__name__ = name if name is not None else func.__name__
   wrapped.__doc__  = func.__doc__
   wrapped.__dict__.update ( func.__dict__ )
   if mark_as_alias:
      wrapped.is_alias = True

   return wrapped
# --- end of fcopy (...) ---

class RingBuffer ( collections.deque ):
   def __init__ ( self, max_size ):
      super ( RingBuffer, self ).__init__()
      self.max_size = int ( max_size )

   def reset ( self, max_size=None ):
      if max_size is not None:
         self.max_size = int ( max_size )
      self.clear()

   def is_full ( self ):
      return len ( self ) >= self.max_size

   def append ( self, value ):
      if self.is_full():
         self.popleft()
      super ( RingBuffer, self ).append ( value )


class CommandHistory ( RingBuffer ):

   def __init__ ( self, max_size=100 ):
      super ( CommandHistory, self ).__init__ ( max_size=max_size )




class ConsoleException ( Exception ):
   pass

class ConsoleStatusException ( ConsoleException ):
   pass

class ConsoleInterpreterStatus ( object ):
   """Object that represents the status of a ConsoleInterpreter."""

   # STATE := {0..N}
   # overall, there are 4 (5) states
   # * the undefined state
   # * exiting
   # * ready to parse
   # * parsing a command
   # * executing a command
   #
   STATE_UNDEF     = 0
   STATE_QUIT      = 1
   STATE_READY     = 2
   STATE_CMD_PARSE = 3
   STATE_CMD_EXEC  = 4

   STATE_TRANSITION_TABLE = {
      STATE_UNDEF     : frozenset(),
      STATE_QUIT      : frozenset(),
      STATE_READY     : frozenset ({ STATE_CMD_PARSE, STATE_CMD_EXEC }),
      STATE_CMD_PARSE : frozenset ({
         STATE_READY, STATE_CMD_EXEC, STATE_CMD_PARSE
      }),
      STATE_CMD_EXEC  : frozenset ({ STATE_READY, STATE_QUIT }),
   }

   # FLAGS := {0,} | {2^k for k in 0..N}
   FLAGS_UNDEF      = 0
   FLAGS_CONFIGURED = 1
   FLAGS_ONERROR    = 2

   @classmethod
   def get_state ( cls, name ):
      return getattr ( cls, "STATE_" + name.upper() )
   # --- end of get_state (...) ---

   def __init__ ( self ):
      super ( ConsoleInterpreterStatus, self ).__init__()
      self.state = self.STATE_UNDEF
      self.flags = self.FLAGS_UNDEF
   # --- end of __init__ (...) ---

   def set_flag ( self, flag ):
      self.flags |= flag

   def clear_flag ( self, flag ):
      self.flags &= ~flag

   def has_flag ( self, flag ):
      return bool ( self.flags & flag )

   def set_configured ( self ):
      self.flags |= self.FLAGS_CONFIGURED
   # --- end of set_configured (...) ---

   def reset ( self ):
      self.state = self.STATE_READY
      self.clear_flag ( self.FLAGS_ONERROR )
   # --- end of reset (...) ---

   def __eq__ ( self, other ):
      if isinstance ( other, int ):
         return self.state == other
      else:
         raise NotImplementedError()

   def __ne__ ( self, other ):
      if isinstance ( other, int ):
         return self.state != other
      else:
         raise NotImplementedError()


   def goto ( self, next_state ):
      """state transition"""
      #if "self.state => next_state" allowed
      #returns ??

      i_next_state = self.get_state ( next_state )

      if i_next_state in self.STATE_TRANSITION_TABLE [self.state]:
         self.state = i_next_state
         return True
      else:
         raise ConsoleStatusException (
            "invalid state transition {src}->{dest} ({name!r}).".format (
               src=self.state, dest=self.get_state ( next_state ),
               name=next_state
            )
         )
   # --- end of goto (...) ---

   def force ( self, next_state="READY" ):
      """forced state transitition"""
      self.state = self.get_state ( next_state )
      return True
   # --- end of force (...) ---

   def is_paused ( self ):
      return False

   #def __str__ ...


# --- end of ConsoleInterpreterStatus ---

class ConsoleInterpreter ( cmd.Cmd ):
   # TODO: line continuation when "\" at the end of a line

   def __init__ ( self, *args, **kwargs ):
      super ( ConsoleInterpreter, self ).__init__ ( *args, **kwargs )
      self.state      = ConsoleInterpreterStatus()
      self.interface  = None

      self._locals  = {}
      # for printing the history
      self._history = CommandHistory()
      # name => real command name
      self._alias  = {}
      self._cmdbuffer = None

      self.MULTILINE_JOIN = ' '

      self.DEFAULT_PS1 = 'cmd %'
      self.DEFAULT_PS2 = '>'
      #self.PS3 = ''
      #self.PS4 = '+ '

      self.intro  = "roverlay console"

      self.setup_aliases()
   # --- end of __init__ (...) ---

   def setup_aliases ( self ):
      pass
   # --- end of setup_aliases (...) ---

   def is_onerror ( self ):
      return self.state.has_flag ( ConsoleInterpreterStatus.FLAGS_ONERROR )
   # --- end of is_onerror (...) ---

   def set_onerror ( self ):
      return self.state.set_flag ( ConsoleInterpreterStatus.FLAGS_ONERROR )
   # --- end of set_onerror (...) ---

   def clear_onerror ( self ):
      return self.state.clear_flag ( ConsoleInterpreterStatus.FLAGS_ONERROR )
   # --- end of clear_onerror (...) ---

   def add_alias ( self, dest, *aliases ):
      if hasattr ( self, 'do_' + dest ):
         for alias in aliases:
            self._alias [alias] = dest
         return True
      elif self.state == ConsoleInterpreterStatus.STATE_UNDEF:
         raise AssertionError ( "no such function: do_{}".format ( dest ) )
      else:
         sys.stderr.write ( "alias: do_{} does not exist\n".format ( dest ) )
         return False

   def reset ( self, soft=True ):
      self.state.reset()
      self._cmdbuffer = None
      self.prompt = self._locals.get ( "PS1", self.DEFAULT_PS1 ) + ' '

   def unalias_cmdline ( self, line ):
      if line:
         lc = line.split ( None, 1 )
         unaliased = self._alias.get ( lc[0] ) if lc[0] else None

         if unaliased:
            if len ( lc ) > 1:
               return unaliased + ' ' + lc[1]
            else:
               return unaliased
         else:
            return line
      else:
         return line
   # --- end of unalias_cmdline (...) ---

   def warn_usage ( self ):
      sys.stderr.write ( "{}: bad usage.\n".format ( self.lastcmd ) )

   def get_argbuffer ( self ):
      return self._cmdbuffer[1:]
   # --- end of get_linebuffer (...) ---

   def precmd ( self, line ):
      sline = line.strip()

      if sline and sline[-1] == chr ( 92 ):
         # "\" at end of line => line continuation
         self.state.goto ( "CMD_PARSE" )
         self.prompt = self._locals.get ( "PS2", self.DEFAULT_PS2 ) + ' '

         if self._cmdbuffer is None:
            # unalias
            self._cmdbuffer = sline[:-1].rstrip().split ( None, 1 )
            if self._cmdbuffer[0] in self._alias:
               self._cmdbuffer[0] = self._alias [self._cmdbuffer[0]]
         else:
            self._cmdbuffer.append ( sline[:-1].rstrip() )

         return ""
      elif self._cmdbuffer:
         self._cmdbuffer.append ( sline )

         self.state.goto ( "CMD_EXEC" )
         return self.MULTILINE_JOIN.join ( self._cmdbuffer )
      else:
         # unalias
         self.state.goto ( "CMD_EXEC" )
         return self.unalias_cmdline ( line )
   # --- end of precmd (...) ---

   def postcmd ( self, stop, line ):
      if self.state == ConsoleInterpreterStatus.STATE_CMD_EXEC:
         if self.is_onerror():
            self.clear_onerror()
         elif self.lastcmd != "history":
            self._history.append ( line )

         self.state.goto ( "READY" )
         self._cmdbuffer = None
         self.prompt = self._locals.get ( "PS1", self.DEFAULT_PS1 ) + ' '

      return stop
   # --- end of postcmd (...) ---

   def onecmd ( self, *a, **b ):
      if self.state == ConsoleInterpreterStatus.STATE_CMD_EXEC:
         return super ( ConsoleInterpreter, self ).onecmd ( *a, **b )
      else:
         # suppress command
         return None
   # --- end of onecmd (...) ---

   def emptyline ( self ):
      pass
   # -- end of emptyline (...) ---

   def preloop ( self ):
      if not self.state.is_paused():
         self.reset ( soft=True )
   # --- end of preloop (...) ---

   def setup ( self, interface ):
      self.interface = interface
      self.state.set_configured()
      return True
   # --- end of setup (...) ---

   def do_alias ( self, line ):
      """Show/set aliases (currently only shows all aliases)."""
      alen = 1 + len ( max ( self._alias, key=lambda k: len ( k ) ) )

      sys.stdout.write ( '\n'.join (
         "{:<{l}} is {!r}".format ( alias, name, l=alen )
            for alias, name in self._alias.items()
      ) )
      sys.stdout.write ( '\n' )
   # --- end of do_alias (...) ---

   def do_unalias ( self, line ):
      """Unsets an alias."""
      sys.stderr.write ( "unalias: method stub\n" )
   # --- end of do_unalias (...) ---

   def do_history ( self, line ):
      """Shows the command history."""
      sys.stdout.write ( '\n'.join ( l for l in self._history ) )
      sys.stdout.write ( '\n' )
   # --- end of history (...) ---

   def do_set ( self, line ):
      """Sets a variable.

      Usage: set VAR=VALUE

      Examples:
      * set PS1=cmd %
      * set dep=fftw 3
      """
      name, sepa, value = line.partition ( '=' )
      if not sepa:
         sys.stderr.write ( "set, bad syntax: {}\n".format ( line ) )
      else:
         self._locals [name.strip()] = value
   # --- end of do_set (...) ---

   def do_unset ( self, line ):
      """Unsets zero or more variables.

      Usage: unset VAR0 [VAR1...]

      Examples:
      * unset PS1
      """
      for varname in line.split ( None ):
         try:
            del self._locals [varname]
         except KeyError:
            pass
   # --- end of do_unset (...) ---

   def do_quit ( self, *a ):
      """Exit"""
      sys.stdout.flush()
      sys.stderr.flush()
      self.state.goto ( "QUIT" )
      return True

   def do_exit ( self, *a ):
      """Exit"""
      return self.do_quit()

   def do_q ( self, *a ):
      """Exit"""
      return self.do_quit()

   def do_EOF ( self, *a ):
      """Exit"""
      sys.stdout.write ( '\n' )
      return self.do_quit()
# --- end of ConsoleInterpreter ---
