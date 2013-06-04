# R overlay -- roverlay package, util
# -*- coding: utf-8 -*-
# Copyright (C) 2012 André Erdmann <dywi@mailerd.de>
# Distributed under the terms of the GNU General Public License;
# either version 2 of the License, or (at your option) any later version.

"""provides utility functions commonly used"""

__all__= [
   'dodir', 'keepenv', 'sysnop', 'get_dict_hash', 'priosort',
   'for_all_files'
]

import os
import logging

LOGGER = logging.getLogger ( 'util' )

def for_all_files (
   files_or_dirs, func,
   args=(), kwargs={}, file_filter=None, ignore_missing=False
):
   """
   Runs "func ( <file>, *args, **kwargs )" for each <file> in files_or_dirs.
   Dirs will be recursively "expanded" (= for all files/dirs in dir...).

   arguments:
   * files_or_dirs  -- an iterable with files or dirs
   * func           -- function that will be called for each file
   * args           -- args that will be passed to each func call
                        Defaults to () (empty tuple)
   * kwargs         -- keyword args that will be passed to each func call
                        Defaults to {} (empty dict)
   * file_filter    -- if not None: func will only be called if this function
                                    returns True for <file>
                        Defaults to None
   * ignore_missing -- if True: do not raise an exception if a file/dir is
                                missing
                        Defaults to False
   """
   # alternative: os.walk()
   def recursive_do ( fpath ):
      if os.path.isfile ( fpath ):
         if file_filter is None or file_filter ( fpath ):
            func ( fpath, *args, **kwargs )
      elif os.path.isdir ( fpath ):
         for fname in os.listdir ( fpath ):
            recursive_do ( fpath + os.sep + fname )
      elif os.access ( fpath, os.F_OK ):
         raise Exception ( "{}: neither a file nor a dir.".format ( fpath ) )
      elif not ignore_missing:
         raise Exception ( "{!r} does not exist!".format ( fpath ) )
   # --- end of recursive_do (...) ---

   for f in files_or_dirs:
      recursive_do ( f )
# --- end of for_all_files (...) ---

def priosort ( iterable ):
   """Sorts the items of an iterable by priority (lower value means higher
   priority).

   arguments:
   * iterable
   """
   def priokey ( item ):
      """Returns the priority of an item.

      arguments:
      * item --
      """
      return item.priority
   # --- end of priokey (...) ---

   return sorted ( iterable, key=priokey )
# --- end of priosort (...) ---

def get_dict_hash ( kwargs ):
   # dict is not hashable, instead hash a frozenset of (key,value) tuples
   # !!! this operations costs (time)
   return hash (
      frozenset (
         ( k, v ) for k, v in kwargs.items()
      )
   )
# --- end of get_dict_hash (...) ---


def keepenv ( *to_keep ):
   """Selectively imports os.environ.

   arguments:
   * *to_keep -- env vars to keep

   to_keep  ::= <env_item> [, <env_item>]*
   env_item ::= <env_key> | tuple ( <env_key> [, <env_key>], <fallback> )

   example:
   keepenv (
      ( 'PATH', '/bin:/usr/bin' ), ( ( 'USER', 'LOGNAME' ), 'user' ),
      PORTDIR
   )
   keeps PATH (with fallback value if unset), USER/LOGNAME (/w fallback) and
   PORTDIR (only if set).
   """
   myenv = dict()

   for item in to_keep:
      if ( not isinstance ( item, str ) ) and hasattr ( item, '__iter__' ):
         var      = item [0]
         fallback = item [1]
      else:
         var      = item
         fallback = None

      if isinstance ( var, str ):
         if var in os.environ:
            myenv [var] = os.environ [var]
         elif fallback is not None:
            myenv [var] = fallback
      else:
         varlist = var
         for var in varlist:
            if var in os.environ:
               myenv [var] = os.environ [var]
            elif fallback is not None:
               myenv [var] = fallback

   # -- for
   return myenv
# --- end of keepenv (...) ---

def sysnop ( nop_returns_success=True, format_str=None, old_formatting=False ):
   """Tries to find a no-op system executable, typically /bin/true or
   /bin/false, depending on whether the operation should succeed or fail.

   arguments:
   * nop_returns_success -- whether the no-op should return success
                             (/bin/true, /bin/echo) or failure (/bin/false)
   * format_str          -- optional; if set and not None:
                              also return format_str.format ( nop=<no-op>)
   * old_formatting      -- use old formatting for format_str (str % tuple
                             instead of str.format ( *tuple ))

   returns: no-op command as tuple, optionally with the formatted string
            as 2nd element or None if no no-op found
   """
   if nop_returns_success:
      candidates = ( '/bin/true', '/bin/echo' )
   else:
      candidates = ( '/bin/false' )

   for c in candidates:
      if os.path.isfile ( c ):
         if format_str:
            if not old_formatting:
               return ( c, format_str.format ( nop=c ) )
            else:
               return ( c, format_str % c )
         else:
            return ( c, )

   return None
# --- end of sysnop (...) ---

def dodir ( directory, mkdir_p=False, **makedirs_kw ):
   """Ensures that a directory exists (by creating it, if necessary).

   arguments:
   * directory     --
   * mkdir_p       -- whether to create all necessary parent directories or not
                      Defaults to False
   * **makedirs_kw -- keywords args for os.makedirs() (if mkdir_p is True)

   returns: True if directory exists else False
   """
   if os.path.isdir ( directory ): return True
   try:
      if mkdir_p:
         os.makedirs ( directory, **makedirs_kw )
      else:
         os.mkdir ( directory )

      return True
   except Exception as e:
      LOGGER.exception ( e )
      return os.path.isdir ( directory )

# --- end of dodir (...) ---
