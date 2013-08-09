# R overlay -- roverlay package, argutil
# -*- coding: utf-8 -*-
# Copyright (C) 2012, 2013 André Erdmann <dywi@mailerd.de>
# Distributed under the terms of the GNU General Public License;
# either version 2 of the License, or (at your option) any later version.

import os
import argparse
import pwd
import grp

def get_uid ( user ):
   try:
      return int ( user )
      #pwd.getpwuid(^).pw_uid
   except ValueError:
      pass
   return pwd.getpwnam ( user ).pw_uid

def get_gid ( group ):
   try:
      return int ( group )
      #grp.getgrgid(^).gr_gid
   except ValueError:
      pass
   return grp.getgrnam ( group ).gr_gid

def is_uid ( value ):
   try:
      return get_uid ( value )
   except:
      pass
   raise argparse.ArgumentTypeError (
      "no such user/uid: {}".format ( value )
   )

def is_gid ( value ):
   try:
      return get_gid ( value )
   except:
      pass
   raise argparse.ArgumentTypeError (
      "no such group/gid: {}".format ( value )
   )

def is_fs_file ( value ):
   f = os.path.abspath ( value )
   if not os.path.isfile ( f ):
      raise argparse.ArgumentTypeError (
         "{!r} is not a file.".format ( value )
      )
   return f

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

def is_fs_dir ( value ):
   d = os.path.abspath ( value )
   if not os.path.isdir ( d ):
      raise argparse.ArgumentTypeError (
         "{!r} is not a directory.".format ( value )
      )
   return d

def is_fs_file_or_dir ( value ):
   f = os.path.abspath ( value )
   if os.path.isdir ( f ) or os.path.isfile ( f ):
      return f
   else:
      raise argparse.ArgumentTypeError (
         "{!r} is neither a file nor a directory.".format ( value )
      )

def couldbe_fs_dir ( value ):
   d = os.path.abspath ( value )
   if os.path.exists ( d ) and not os.path.isdir ( d ):
      raise argparse.ArgumentTypeError (
         "{!r} cannot be a directory.".format ( value )
      )
   return d

def is_fs_dir_or_void ( value ):
   if value:
      return is_fs_dir ( value )
   else:
      return ''

def is_fs_file_or_void ( value ):
   if value:
      return is_fs_file ( value )
   else:
      return ''


class ArgumentParserError ( Exception ):
   pass

class ArgumentGroupExists ( ArgumentParserError ):
   pass

class ArgumentFlagException ( ArgumentParserError ):
   pass


class ArgumentParserProxy ( object ):

   ARG_ADD_DEFAULT  = 2**0
   # OPT_IN: store True
   ARG_OPT_IN       = 2**1
   # OPT_OUT: store False
   ARG_OPT_OUT      = 2**2
   ARG_SHARED       = 2**4
   ARG_HELP_DEFAULT = 2**5
   ARG_META_FILE    = 2**6
   ARG_META_DIR     = 2**7
   ARG_INVERSE      = 2**8

   ARG_SHARED_INVERSE = ARG_SHARED | ARG_INVERSE
   ARG_META_FILEDIR   = ARG_META_FILE | ARG_META_DIR
   ARG_WITH_DEFAULT   = ARG_ADD_DEFAULT | ARG_HELP_DEFAULT

   STR_TRUE     = 'enabled'
   STR_FALSE    = 'disabled'
   STR_SUPPRESS = 'keep'




   def __init__ ( self, defaults=None, **kwargs ):
      super ( ArgumentParserProxy, self ).__init__()
      self.parser = argparse.ArgumentParser (**kwargs )

      if defaults is None:
         self.defaults = dict()
      elif isinstance ( defaults, dict ):
         self.defaults = defaults
      else:
         self.defaults = dict ( defaults )

      self._argument_groups = dict()

      self.parsed = None
   # --- end of __init__ (...) ---

   def get_default ( self, key, *args ):
      return self.defaults.get ( key, *args )
   # --- end of get_default (...) ---

   def apply_arg_flags ( self, kwargs, flags ):

      if flags & self.ARG_SHARED and 'default' not in kwargs:
         kwargs ['default'] = argparse.SUPPRESS

      if flags & self.ARG_OPT_IN:
         if flags & self.ARG_OPT_OUT:
            raise ArgumentFlagException (
               "opt-in and opt-out are mutually exclusive."
            )
         else:
            kwargs ['action']  = 'store_true'
            if 'default' not in kwargs:
               kwargs ['default'] = False

      elif flags & self.ARG_OPT_OUT:
         kwargs ['action']  = 'store_false'
         if 'default' not in kwargs:
            kwargs ['default'] = True
      # -- end if <opt-in/opt-out>

      if flags & self.ARG_ADD_DEFAULT:
         if 'defkey' in kwargs:
            key = kwargs.pop ( 'defkey' )
##         elif 'dest' in kwargs:
         else:
            key = kwargs ['dest']
##         else:
##            key = args[0].lstrip ( '-' ).lower().replace ( '-', '_' )

         if 'default' in kwargs:
            fallback = kwargs.pop ( "default" )
            kwargs ['default'] = self.defaults.get ( key, fallback )
         else:
            kwargs ['default'] = self.defaults [key]

      # -- end if <ARG_ADD_DEFAULT>

      if flags & self.ARG_HELP_DEFAULT:
         default = kwargs.get ( 'default', None )
         if default is argparse.SUPPRESS:
            default_str = self.STR_SUPPRESS

         elif default in { True, False }:
            if flags & self.ARG_INVERSE:
               default_str = self.STR_FALSE if default else self.STR_TRUE
            else:
               default_str = self.STR_TRUE if default else self.STR_FALSE

         else:
            default_str = '%(default)s'
         # -- end if

         if default_str:
            if 'help' in kwargs:
               kwargs ['help'] = kwargs ['help'] + ' [' + default_str + ']'
            else:
               kwargs ['help'] = '[' + default_str + ']'
      # -- end if <append default value to help>

      if flags & self.ARG_META_DIR:
         if flags & self.ARG_META_FILE:
            kwargs ['metavar'] = '<file|dir>'
         else:
            kwargs ['metavar'] = '<dir>'
      elif flags & self.ARG_META_FILE:
         kwargs ['metavar'] = '<file>'
      # -- end if <metavar>

      return kwargs
   # --- end of apply_arg_flags (...) ---

   def convert_kwargs ( self, kwargs, flags=0 ):
      if 'flags' in kwargs:
         kwargs_copy = dict ( kwargs )
         my_flags    = kwargs_copy.pop ( "flags" ) | flags
         return self.apply_arg_flags ( kwargs_copy, my_flags )
      elif flags:
         return self.apply_arg_flags ( dict ( kwargs ), flags )
      else:
         return kwargs
   # --- end of convert_kwargs (...) ---

   def arg ( self, *args, **kwargs ):
      return self.parser.add_argument (
         *args, **self.convert_kwargs ( kwargs )
      )
   # --- end of arg (...) ---

   def get_group_arg_adder ( self, key ):
      def wrapped_group_arg ( *args, **kwargs ):
         return self.group ( key ).add_argument (
            *args, **self.convert_kwargs ( kwargs )
         )
      # --- end of wrapped_group_arg (...) ---

      wrapped_group_arg.__doc__ = self.group_arg.__doc__
      wrapped_group_arg.__name__ = self.group_arg.__name__
      wrapped_group_arg.__dict__.update ( self.group_arg.__dict__ )
      return wrapped_group_arg
   # --- end of get_group_arg_adder (...) ---

   def group_arg ( self, key, *args, **kwargs ):
      return self.group ( key ).add_argument (
         *args, **self.convert_kwargs ( kwargs )
      )
   # --- end of group_arg (...) ---

   def parse_args ( self, *args, **kwargs ):
      self.parsed = self.parser.parse_args ( *args, **kwargs )
      return self.parsed
   # --- end of parse_args (...) ---

   def parse ( self, *args, **kwargs ):
      return self.parse_args ( *args, **kwargs )
   # --- end of parse (...) ---

   def add_argument_group ( self, key, **kwargs ):
      if key in self._argument_groups:
         raise ArgumentGroupExists ( key )
      else:
         self._argument_groups [key] = (
            self.parser.add_argument_group ( **kwargs )
         )
         return self.get_group_arg_adder ( key )
   # --- end of add_argument_group (...) ---

   def group ( self, key ):
      return self._argument_groups [key]
   # --- end of group (...) ---

# --- end of ArgumentParserProxy ---
