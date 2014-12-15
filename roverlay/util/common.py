# R overlay -- roverlay package, util
# -*- coding: utf-8 -*-
# Copyright (C) 2012 André Erdmann <dywi@mailerd.de>
# Distributed under the terms of the GNU General Public License;
# either version 2 of the License, or (at your option) any later version.

"""provides utility functions commonly used"""

__all__= [
   'dodir', 'dodir_for_file',
   'for_all_files_decorator', 'for_all_files',
   'get_dict_hash', 'keepenv', 'keepenv_v',
   'priosort', 'sysnop', 'getsize', 'is_vcs_dir', 'is_not_vcs_dir',
    'headtail', 'try_unlink', 'get_pwd_info', 'get_home_dir',
]


import errno
import os
import sys
import logging
import pwd

LOGGER = logging.getLogger ( 'util' )

# COULDFIX: add .svn et al.
#
VCS_DIRNAMES = frozenset ({ '.git', })


def headtail ( iterable ):
   return ( iterable[0], iterable[1:] )
# --- end of headtail #py2 (...) ---

def try_unlink ( fspath ):
   """Tries to remove a file. Does not fail if the file did not exist.

   Returns: True if a file has been removed, else False.

   arguments:
   * fspath --
   """
   try:
      os.unlink ( fspath )
   except OSError as oserr:
      if oserr.errno == errno.ENOENT:
         return False
      else:
         raise
   else:
      return True
# --- end of try_unlink (...) ---

def for_all_files_decorator (
   func, args=(), kwargs={},
   file_filter=None, ignore_missing=False, dir_filter=True,
   kwargs_union=0, topdown=True, onerror=None, followlinks=False,
):
   """
   Returns a function that runs "func ( <file>, *args, **kwargs )"
   for each <file> in files_or_dirs (its first argument).
   Dirs will be recursively "expanded" (= for all files/dirs in dir...).

   arguments:
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
   * dir_filter     -- if True         : vcs dirs will be ignored
                       else if not None: dir will be ignored unless
                                         this function returns True for <dir>
                        Defaults to True
   * kwargs_union   -- an int that controls how/which kwargs are passed to func
                       0: always pass decorator kwargs
                       1: update decorator kwargs with caller kwargs
                       2: update caller kwargs with decorator kwargs
   * topdown        -- see os.walk(). Defaults to True.
   * onerror        -- see os.walk(). Defaults to None.
   * followlinks    -- see os.walk(). Defaults to False.
   """
   OUR_DIR_FILTER = None if dir_filter is None else (
      is_not_vcs_dir if dir_filter is True else dir_filter
   )

   def wrapped ( files_or_dirs, *their_args, **their_kwargs ):
      my_args = their_args or args
      if kwargs_union == 0:
         my_kwargs = kwargs
      elif kwargs_union == 1:
         my_kwargs = dict ( kwargs )
         my_kwargs.update ( their_kwargs )
      else:
         my_kwargs = dict ( their_kwargs )
         my_kwargs.update ( kwargs )


      func_result = dict()

      for item in (
         files_or_dirs if (
            not isinstance ( files_or_dirs, str )
            and hasattr ( files_or_dirs, '__iter__' )
         )
         else ( files_or_dirs, )
      ):
         if os.path.isfile ( item ):
            if file_filter is None or file_filter ( item ):
               func_result [item] = func ( item, *args, **kwargs )
         elif os.path.isdir ( item ):
            partial_result = dict()
            for root, dirnames, filenames in os.walk (
               item,
               topdown=topdown, onerror=onerror, followlinks=followlinks
            ):
               if OUR_DIR_FILTER is None or OUR_DIR_FILTER ( root ):
                  for filename in filenames:
                     fpath = root + os.sep + filename
                     if file_filter is None or file_filter ( fpath ):
                        partial_result [fpath ] = func (
                           fpath, *args, **kwargs
                        )
               # -- end if OUR_DIR_FILTER
            # -- end for root...
            func_result [item] = partial_result
            partial_result = None

         elif os.access ( item, os.F_OK ):
            raise Exception ( "{}: neither a file nor a dir.".format ( item ) )

         elif not ignore_missing:
            raise Exception ( "{!r} does not exist!".format ( item ) )
      # -- end for item

      return func_result
   # --- end of wrapped (...) ---

   wrapped.__name__ = func.__name__
   wrapped.__doc__  = func.__doc__
   wrapped.__dict__.update ( func.__dict__ )
   return wrapped
# --- end of for_all_files_decorator (...) ---

def for_all_files (
   files_or_dirs, func, args=(), kwargs={},
   file_filter=None, ignore_missing=False, dir_filter=True
):
   """Wraps func and calls it several times (for each file).
   See for_all_files_decorator() for details.
   """
   return for_all_files_decorator (
      func, args=args, kwargs=kwargs, file_filter=file_filter,
      ignore_missing=ignore_missing, dir_filter=dir_filter,
      kwargs_union=0
   ) ( files_or_dirs )
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

def keepenv_v ( to_keep ):
   """Selectively imports os.environ.

   arguments:
   * *to_keep -- env vars to keep

   to_keep  ::= <env_item> [, <env_item>]*
   env_item ::= <env_key> | tuple ( <env_key> [, <env_key>], <fallback> )

   example:
   keepenv_v (
      ( 'PATH', '/bin:/usr/bin' ), ( ( 'USER', 'LOGNAME' ), 'user' ),
      'PORTDIR'
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
# --- end of keepenv_v (...) ---

def keepenv ( *to_keep ):
   return keepenv_v ( to_keep )
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
      candidates = ( '/bin/false', )

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

def dodir ( directory, mkdir_p=False, log_exception=True, **makedirs_kw ):
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
   except OSError as e:
      if log_exception:
         LOGGER.exception ( e )
      return os.path.isdir ( directory )

# --- end of dodir (...) ---

def dodir_for_file ( filepath, mkdir_p=True, **kw ):
   return dodir ( os.path.dirname ( filepath ), mkdir_p=mkdir_p, **kw )
# --- end of dodir_for_file (...) ---

def getsize ( filepath ):
   """Returns the size of the given file.

   arguments:
   * filepath --
   """
   return os.stat ( filepath ).st_size
# --- end of getsize (...) ---

def is_vcs_dir ( dirpath ):
   """Returns True if dirpath could be a directory maintained by a version
   control system, e.g. git.

   arguments:
   * dirpath --
   """
   return os.path.basename ( dirpath.rstrip ( os.sep ) ) in VCS_DIRNAMES
# --- end of is_vcs_dir (...) ---

def is_not_vcs_dir ( dirpath ):
   return not is_vcs_dir ( dirpath )
# --- end of is_not_vcs_dir (...) ---

def get_pwd_info ( user=None ):
   """Returns the passwd entry of the given user.

   arguments:
   * user -- name, uid or None (os.getuid()). Defaults to None.
   """
   if user is None:
      return pwd.getpwuid ( os.getuid() )
   elif isinstance ( user, int ):
      return pwd.getpwuid ( user )
   else:
      try:
         uid = int ( user, 10 )
      except ValueError:
         return pwd.getpwnam ( user )
      else:
         return pwd.getpwuid ( uid )
# --- end of get_pwd_info (...) ---

def get_home_dir ( user=None ):
   """Returns a user's home directory.

   arguments:
   * user -- name, uid or None (os.getuid()). Defaults to None.
   """
   return get_pwd_info ( user ).pw_dir
# --- end of get_home_dir (...) ---
