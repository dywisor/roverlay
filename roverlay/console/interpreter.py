# R overlay --
# -*- coding: utf-8 -*-
# Copyright (C) 2013 André Erdmann <dywi@mailerd.de>
# Distributed under the terms of the GNU General Public License;
# either version 2 of the License, or (at your option) any later version.

import argparse
import errno
import collections
import os
import sys
import cmd
import string
import shlex
##import glob

import roverlay.util.fileio
import roverlay.strutil
from roverlay.strutil import unquote, unquote_all

class RingBuffer ( collections.deque ):
   def __init__ ( self, max_size ):
      super ( RingBuffer, self ).__init__()
      self.max_size = int ( max_size )

   def reset ( self, max_size=None, clear=True ):
      if max_size is not None:
         self.max_size = int ( max_size )

      if clear or self.max_size <= 0:
         self.clear()
      else:
         while len ( self ) > self.max_size:
            self.popleft()
   # --- end of reset (...) ---

   def resize ( self, max_size=None ):
      self.reset ( max_size=max_size, clear=False )
   # --- end of resize (...) ---

   def is_full ( self ):
      return len ( self ) >= self.max_size

   def append ( self, value ):
      if self.is_full():
         self.popleft()
      super ( RingBuffer, self ).append ( value )

# --- end of RingBuffer ---

class CommandHistory ( RingBuffer ):

   def __init__ ( self, max_size=100 ):
      super ( CommandHistory, self ).__init__ ( max_size=max_size )

# --- end of CommandHistory ---



class ConsoleException ( Exception ):
   pass

class ConsoleStatusException ( ConsoleException ):
   pass

class ConsoleUsageException ( ConsoleException ):
   pass

class ConsoleArgumentParser ( argparse.ArgumentParser ):

   def exit ( self, status=0, message=None ):
      if message:
         raise ConsoleUsageException ( message )
      else:
         raise ConsoleUsageException()

   def error ( self, message ):
      raise ConsoleUsageException ( message )

   def add_opt_in ( self, *args, **kwargs ):
      self.add_argument (
         *args, default=False, action='store_true', **kwargs
      )

   def add_opt_out ( self, *args, **kwargs ):
      self.add_argument (
         *args, default=True, action='store_false', **kwargs
      )

# --- end of ConsoleArgumentParser ---


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
   # !!! cmd.Cmd is an old-style class

   def __init__ ( self, *args, **kwargs ):
      #super ( ConsoleInterpreter, self ).__init__ ( *args, **kwargs )
      cmd.Cmd.__init__ ( self, *args, **kwargs )


      self.identchars += os.sep
      self.state      = ConsoleInterpreterStatus()
      self.interface  = None

      self._str_formatter = string.Formatter()

      self._locals  = {}
      # for printing the history
      self._history = CommandHistory()
      # name => real command name
      self._alias  = {}
      self._cmdbuffer = None

      self._initial_pwd = os.getcwd()
      self._pwd         = None
      self._oldpwd      = None

      self._chroot      = None

      self.MULTILINE_JOIN = ' '

      self.DEFAULT_PS1 = 'cmd %'
      self.DEFAULT_PS2 = '>'
      #self.PS3 = ''
      #self.PS4 = '+ '

      self.intro  = "roverlay console"

      self._argparser = dict()

      self.setup_aliases()
      self.setup_argparser()
      self.setup_interpreter()
   # --- end of __init__ (...) ---

   def set_var ( self, name, value ):
      self._locals [name] = value
   # --- end of set_var (...) ---

   def set_lastarg ( self, value ):
      return self.set_var ( "_lastarg", value )
   # --- end of set_lastarg (...) ---

   def get_argparser ( self, cmd, create=False ):
      if create:
         parser = self._argparser.get ( cmd, None )
         if parser is None:
            parser = ConsoleArgumentParser ( prog=cmd, add_help=True )
            self._argparser [cmd] = parser
         return parser
      else:
         return self._argparser [cmd]
   # --- end of get_argparser (...) ---

   def parse_cmdline ( self, cmd, line ):
      try:
         ret = self.get_argparser ( cmd, create=False ).parse_args (
            shlex.split ( self.format_locals ( line ) )
         )
      except ConsoleUsageException as cue:
         sys.stderr.write ( str ( cue ) + '\n' )
         ret = None

      return ret
   # --- end of parse_cmdline (...) ---

   def format_locals ( self, line, replace_lastarg=True ):
      if '_lastarg' not in self._locals:
         self.set_lastarg ( "" )

      if replace_lastarg:
         l = line.replace ( '!$', '{_lastarg}' )
      else:
         l = line

      try:
         return self._str_formatter.vformat ( l, (), self._locals )
      except KeyError as kerr:
         raise ConsoleUsageException ( "{!s} is not set.".format ( kerr ) )
   # --- end of format_locals (...) ---

   def get_fspath ( self, line ):
      pline = unquote_all ( line )
      if pline:
         return os.path.normpath ( os.path.join ( self._pwd, pline ) )
      else:
         return self._pwd
   # --- end of get_fspath (...) ---

   def argparse_filepath ( self, value ):
      f = self.get_fspath ( value ) if value else None
      if f and os.path.isfile ( f ):
         return f
      else:
         raise argparse.ArgumentTypeError (
            "{!r} is not a file!".format ( value )
         )
   # --- end of argparse_filepath (...) ---

   def argparse_fspath ( self, value ):
      f = self.get_fspath ( value ) if value else None
      if f and os.path.exists ( f ):
         return f
      else:
         raise argparse.ArgumentTypeError (
            "{!r} does not exist!".format ( value )
         )
   # --- end of argparse_fspath (...) ---

   def set_pwd ( self, newpwd ):
      pwd = os.path.normpath ( newpwd )
      if pwd is not None and pwd != self._pwd:
         self._oldpwd = self._pwd
         self._pwd    = pwd

      self._locals ['PWD']    = self._pwd
      self._locals ['OLDPWD'] = self._oldpwd
   # --- end of set_pwd (...) ---

   def setup_aliases ( self ):
      pass
   # --- end of setup_aliases (...) ---

   def setup_argparser ( self ):
      parser = self.get_argparser ( "cat", create=True )
      parser.add_argument ( "files", metavar='<file>', nargs='*',
         help='files to read', type=self.argparse_filepath,
      )

      parser = self.get_argparser ( "history", create=True )
      parser.add_argument ( "-c", "--clear",
         default=False, action='store_true',
         help="clear history"
      )
   # --- end of setup_argparser (...) ---

   def setup_interpreter ( self ):
      pass
   # --- end of setup_interpreter (...) ---

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
      COMP = lambda a: 'complete_' + a

      lc = dest.split ( None, 1 )

      if lc and lc[0] and hasattr ( self, 'do_' + lc[0] ):
         for alias in aliases:
            self._alias [alias] = dest

            # add ref to complete function (if available)
            comp_func = getattr ( self, COMP ( lc[0] ), None )
            if comp_func is not None:
               setattr ( self, COMP ( alias ), comp_func )
         return True
      elif self.state == ConsoleInterpreterStatus.STATE_UNDEF:
         raise AssertionError ( "no such function: do_{}".format ( dest ) )
      else:
         sys.stderr.write ( "alias: do_{} does not exist\n".format ( dest ) )
         return False

   def reset ( self, soft=True ):
      self.state.reset()
      self._cmdbuffer = None
      self._chroot    = None
      self.prompt     = self._locals.get ( "PS1", self.DEFAULT_PS1 ) + ' '

      self._pwd               = self._initial_pwd
      self._oldpwd            = self._initial_pwd
      self._locals ['PWD']    = self._initial_pwd
      self._locals ['OLDPWD'] = self._initial_pwd
      self.set_lastarg ( "" )
   # --- end of reset (...) ---

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

   def chroot_cmd ( self, line ):
      if not line:
         return self._chroot if self._chroot else line
      elif line[0] == '/':
         return 'chroot ' + line
      elif self._chroot:
         lc = line.split ( None, 1 )
         if lc[0] == 'chroot':
            return line
         else:
            return self._chroot + ' ' + line
      else:
         return line
   # --- end of chroot_cmd (...) ---

   def chroot_allowed ( self, cmd ):
      if hasattr ( self, 'CHROOT_ALLOWED' ):
         return cmd in self.CHROOT_ALLOWED
      else:
         return True
   # --- end of chroot_allowed (...) ---

   def precmd ( self, line ):
      sline = line.strip()

      if sline and sline[-1] == chr ( 92 ):
         # "\" at end of line => line continuation
         self.state.goto ( "CMD_PARSE" )
         self.prompt = self._locals.get ( "PS2", self.DEFAULT_PS2 ) + ' '

         if self._cmdbuffer is None:
            # unalias
            self._cmdbuffer = sline[:-1].rstrip().split ( None, 1 )
            if self._cmdbuffer and self._cmdbuffer[0] in self._alias:
               self._cmdbuffer[0] = self._alias [self._cmdbuffer[0]]
         else:
            self._cmdbuffer.append ( sline[:-1].rstrip() )

         return ""
      elif self._cmdbuffer:
         self._cmdbuffer.append ( sline )

         self.state.goto ( "CMD_EXEC" )
         return self.chroot_cmd (
            self.MULTILINE_JOIN.join ( self._cmdbuffer )
         )
      else:
         # unalias
         self.state.goto ( "CMD_EXEC" )
         return self.chroot_cmd (
            self.unalias_cmdline ( line )
         )
   # --- end of precmd (...) ---

   def postcmd ( self, stop, line ):
      if self.state == ConsoleInterpreterStatus.STATE_CMD_EXEC:
         if self.is_onerror():
            self.clear_onerror()
         elif self.lastcmd and self.lastcmd.split(None,1)[0] != "history":
            self._history.append ( line )

         self.state.goto ( "READY" )
         self._cmdbuffer = None

         if self._chroot:
            self.prompt = self._locals.get (
               "CHROOT_PS1", "({}) %".format ( self._chroot )
            ) + ' '
         else:
            self.prompt = self._locals.get ( "PS1", self.DEFAULT_PS1 ) + ' '


      return stop
   # --- end of postcmd (...) ---

   def onecmd ( self, *a, **b ):
      if self.state == ConsoleInterpreterStatus.STATE_CMD_EXEC:
         return cmd.Cmd.onecmd ( self, *a, **b )
         #return super ( ConsoleInterpreter, self ).onecmd ( *a, **b )
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

   def complete_fspath ( self, text, line, begidx, endidx ):
      # FIXME: why gets an "/" at the beginning of text ignored?
      # (doesn't seem to be related to chrooted commands here)

      dcomponents = line.rsplit ( None, 1 )
      if len ( dcomponents ) > 1:
         dpath = self.get_fspath ( os.path.dirname ( dcomponents[1] ) )
      else:
         dpath = self._pwd

      if os.path.isdir ( dpath ):
         return list (
            ( f + os.sep if os.path.isdir ( dpath + os.sep + f ) else f )
            for f in os.listdir ( dpath ) if f.startswith ( text )
         )
      else:
         return []
   # --- end of complete_fspath (...) ---

   def do_exec ( self, line ):
      """Switch console context (depres/remote/...). (TODO)"""
      sys.stderr.write ( "exec: method stub\n" )
   # --- end of do_exec (...) ---

   def do_alias ( self, line ):
      """Show/set aliases (currently only shows all aliases)."""
      alen = 1 + len ( max ( self._alias, key=lambda k: len ( k ) ) )

      sys.stdout.write ( '\n'.join (
         "{:<{l}} is {}".format ( kv[0], kv[1], l=alen )
         for kv in sorted ( self._alias.items(), key=lambda kv: kv[1] )
      ) )
      sys.stdout.write ( '\n' )
   # --- end of do_alias (...) ---

   def do_unalias ( self, line ):
      """Unsets an alias."""
      sys.stderr.write ( "unalias: method stub\n" )
   # --- end of do_unalias (...) ---

   def do_history ( self, line ):
      """Shows the command history."""
      args = self.parse_cmdline ( "history", line )
      if args.clear:
         self._history.reset()
      else:
         sys.stdout.write ( '\n'.join ( l for l in self._history ) )
         sys.stdout.write ( '\n' )
   # --- end of history (...) ---

   def do_pwd ( self, line ):
      """Prints the current working directory."""
      if not self._pwd:
         self._pwd    = self._initial_pwd
         self._oldpwd = self._initial_pwd
         sys.stdout.write ( self._initial_pwd + '\n' )
      elif os.path.isdir ( self._pwd ):
         sys.stdout.write ( self._pwd + '\n' )
      else:
         sys.stdout.write ( "[virtual] {}\n".format ( self._pwd ) )
   # --- end of do_pwd (...) ---

   def complete_cd ( self, *args, **kw ):
      return self.complete_fspath ( *args, **kw )
   # --- end of complete_cd (...) ---

   def do_cd ( self, line ):
      """Changes the working directory.

      Usage: cd [-|<dir>]

      Examples:
      * cd      -- change working directory to the initial dir
      * cd -    -- change working directory to OLDPWD
      * cd /var -- change working to /var
      """
      pline = unquote_all ( line )
      if not pline:
         self.set_pwd ( self._initial_pwd )
      elif pline == '-':
         self.set_pwd ( self._oldpwd )
      elif self._pwd:
         self.set_pwd ( os.path.join ( self._pwd, pline ) )
      else:
         self.set_pwd ( pline )

      if not self._pwd or not os.path.isdir ( self._pwd ):
         sys.stderr.write (
            "warn: {!r} does not exist.\n".format ( self._pwd )
         )
   # --- end of do_cd (...) ---

   def complete_ls ( self, *args, **kw ):
      return self.complete_fspath ( *args, **kw )
   # --- end of complete_ls (...) ---

   def do_ls ( self, line ):
      """Shows the directory content of the given dir (or the current working
      directory).
      """
      p = self.get_fspath ( line )

      try:
         items = '\n'.join (
            sorted ( os.listdir ( p ), key=lambda k: k.lower() )
         )
      except OSError as oserr:
         if oserr.errno == errno.ENOENT:
            sys.stderr.write ( "ls: {!r} does not exist.\n".format ( p ) )
      else:
         sys.stdout.write ( "{}:\n{}\n".format ( p, items ) )
   # --- end of do_ls (...) ---

   def complete_cat ( self, *args, **kw ):
      return self.complete_fspath ( *args, **kw )
   # --- end of complete_cat (...) ---

   def do_cat ( self, line ):
      """Read files and print them.
      Supports uncompressed and bzip2,gzip-compressed files.
      """
      args = self.parse_cmdline ( "cat", line )
      if args:
         try:
            for fpath in args.files:
               for fline in roverlay.util.fileio.read_text_file ( fpath ):
                  sys.stdout.write ( fline )
               else:
                  self.set_lastarg ( fpath )
         except Exception as err:
            sys.stderr.write ( "cat failed ({}, {})!\n".format (
               err.__class__.__name__, str ( err )
            ) )
   # --- end of do_cat (...) ---

   def do_echo ( self, line ):
      """Prints a message. String formatting '{VARNAME}' is supported."""
      try:
         s = self.format_locals ( line )
      except ( IndexError, KeyError, TypeError, ValueError ):
         sys.stderr.write ( "cannot print {!r}!\n".format ( line ) )
      else:
         sys.stdout.write ( s + '\n' )
   # --- end of do_echo (...) ---

   def do_declare ( self, line ):
      """Prints all variables."""
      for kv in sorted (
         self._locals.items(), key=lambda kv: kv[0].lower()
      ):
         sys.stdout.write ( "{k}=\"{v}\"\n".format ( k=kv[0], v=kv[1] ) )
   # --- end of do_declare (...) ---

   def do_set ( self, line ):
      """Sets a variable or prints all variables.

      Usage: set [VAR=VALUE]

      Examples:
      * set PS1=cmd %
      * set dep=fftw 3
      """
      if not line:
         self.do_declare ( line )
      else:
         name, sepa, value = line.partition ( '=' )
         if not sepa:
            sys.stderr.write ( "set, bad syntax: {}\n".format ( line ) )
         else:
            self.set_var ( name.strip(), value )
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

   def complete_chroot ( self, text, line, begidx, endidx ):
      if hasattr ( self, 'COMP_CHROOT_ALLOWED' ):
         if text:
            c = text.lstrip ( "/" )
            return list (
               k for k in self.COMP_CHROOT_ALLOWED if k.startswith ( c )
            )
         else:
            return list ( self.COMP_CHROOT_ALLOWED )
      else:
         return []
   # --- end of complete_chroot (...) ---

   def do_chroot ( self, line ):
      """Enters or leaves a command chroot.
      A command chroot prefixes all input lines with a command (except for
      chroot commands).

      Usage:
      * chroot        -- query chroot status
      * chroot /      -- leave chroot
      * chroot /<cmd> -- enter chroot for <cmd>
      * /             -- alias to chroot /
      * /<cmd>        -- alias to chroot /<cmd>
      """
      pline = unquote_all ( line )
      sline = pline.lstrip ( "/" ).lstrip()

      if pline == "/":
         self._chroot = None
         self.do_unset ( "CHROOT_PS1" )
      elif not sline:
         if self._chroot:
            sys.stdout.write (
               "current command chroot is {!r}\n".format ( self._chroot )
            )
         else:
            sys.stdout.write ( "no command chroot in use.\n" )
      else:
         cmd = self._alias.get ( sline, sline )
         if not hasattr ( self, 'do_' + cmd ):
            sys.stderr.write ( "no such command: {!r}\n".format ( cmd ) )
         elif cmd != 'chroot' and self.chroot_allowed ( cmd ):
            self._chroot = cmd
         else:
            sys.stderr.write (
               "{!r} cmd chroot is not allowed!\n".format ( cmd )
            )

   # --- end of do_chroot (...) ---

   def do_pyver ( self, *a ):
      """Prints the version of the python interpreter."""
      sys.stdout.write (
         "sys.hexversion = {}\n".format ( hex(sys.hexversion) )
      )
   # --- end of do_pyver (...) ---

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

   def do_qq ( self, *a ):
      """Exit"""
      return self.do_quit()

   def do_EOF ( self, *a ):
      """Exit"""
      sys.stdout.write ( '\n' )
      return self.do_quit()
# --- end of ConsoleInterpreter ---
