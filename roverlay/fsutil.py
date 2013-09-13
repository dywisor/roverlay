# R overlay --
# -*- coding: utf-8 -*-
# Copyright (C) 2013 André Erdmann <dywi@mailerd.de>
# Distributed under the terms of the GNU General Public License;
# either version 2 of the License, or (at your option) any later version.

import errno
import functools
import os
import pwd
import stat
import sys

import roverlay.util.common
import roverlay.util.objects

_OS_CHOWN = getattr ( os, 'lchown', os.chown )
_OS_CHMOD = getattr ( os, 'lchmod', os.chmod )


def walk_up ( dirpath, topdown=False, max_iter=None ):
   path_elements = os.path.normpath ( dirpath ).split ( os.sep )

   if path_elements:
      p_start = 0 if path_elements[0] else 1

      if max_iter is None:
         high = len ( path_elements )
      else:
         high = min ( max_iter + p_start, len ( path_elements ) )


      if topdown:
         for k in range ( p_start+1, high+1 ):
            yield os.sep.join ( path_elements[:k] )
      else:
         for k in range ( high, p_start, -1 ):
            yield os.sep.join ( path_elements[:k] )

# --- end of walk_up (...) ---

def get_fs_dict (
   initial_root, create_item=None, dict_cls=dict,
   dirname_filter=None, filename_filter=None,
   include_root=False, prune_empty=False,
):
   # http://code.activestate.com/recipes/577879-create-a-nested-dictionary-from-oswalk/
   fsdict         = dict_cls()
   my_root        = os.path.abspath ( initial_root )

   dictpath_begin = (
      1 + ( my_root.rfind ( os.sep ) if include_root else len ( my_root ) )
   )

   for root, dirnames, filenames in os.walk ( initial_root ):
      if dirname_filter:
         dirnames[:] = [ d for d in dirnames if dirname_filter ( d ) ]

      if filename_filter:
         filenames[:] = [ f for f in filenames if filename_filter ( f ) ]

      if not prune_empty or filenames or dirnames:
         dict_relpath = root[dictpath_begin:]

         if dict_relpath:
            dictpath = dict_relpath.split ( os.sep )
            parent   = functools.reduce ( dict_cls.get, dictpath[:-1], fsdict )

            if create_item is None:
               parent [dictpath[-1]] = dict_cls.fromkeys ( filenames )
            else:
               parent [dictpath[-1]] = dict_cls (
                  (
                     fname,
                     create_item ( ( root + os.sep + fname ), fname, root )
                  )
                  for fname in filenames
               )
   # -- end for

   return fsdict
# --- end of get_fs_dict (...) ---

def create_subdir_check ( parent, fs_sep=os.sep ):
   PARENT_PATH = parent.rstrip ( fs_sep ).split ( fs_sep )

   def is_subdir ( dirpath ):
      return all (
         this == expect for this, expect in zip (
            dirpath.rstrip ( fs_sep ).split ( fs_sep ),
            PARENT_PATH
         )
      )
   # --- end of is_subdir (...) ---

   return is_subdir
# --- end of create_subdir_check (...) ---


def pwd_expanduser ( fspath, uid ):
   if not fspath or fspath[0] != '~':
      return fspath
   elif len ( fspath ) < 2:
      return pwd.getpwuid ( uid ).pw_dir
   elif fspath[1] == os.sep:
      return pwd.getpwuid ( uid ).pw_dir + fspath[1:]
   else:
      return fspath
# --- end of pwd_expanduser (...) ---

def get_bitwise_sum ( iterable, initial_value=None ):
   ret = initial_value if initial_value is not None else 0
   for item in iterable:
      ret |= item
   return ret
# --- end of get_bitwise_sum (...) ---

def get_stat_mode ( mode_str ):

   def iter_mode_values ( mode_str ):
      # rwxrwxrwx
      # 012345678
      # r -> pos % 3 == 0
      # w -> pos % 3 == 1
      # x -> pos % 3 == 2


      # COULDFIX: parse sticky bit etc. (not necessary, currently)
      if len ( mode_str ) > 9:
         raise ValueError ( mode_str )

      for pos, char in enumerate ( mode_str ):
         if char != '-':
            block  = pos // 3
            subpos = pos % 3
            if subpos == 0:
               # r
               assert char == 'r'
               if block == 0:
                  yield stat.S_IRUSR
               elif block == 1:
                  yield stat.S_IRGRP
               else:
                  yield stat.S_IROTH

            elif subpos == 1:
               # w
               assert char == 'w'
               if block == 0:
                  yield stat.S_IWUSR
               elif block == 1:
                  yield stat.S_IWGRP
               else:
                  yield stat.S_IWOTH

            elif subpos == 2:
               # x
               assert char == 'x'
               if block == 0:
                  yield stat.S_IXUSR
               elif block == 1:
                  yield stat.S_IXGRP
               else:
                  yield stat.S_IXOTH

   # --- end of iter_mode_values (...) ---

   return get_bitwise_sum ( iter_mode_values ( mode_str ) )
# --- end of get_stat_mode (...) ---

class ChownChmod ( object ):

   def __init__ ( self, uid=None, gid=None, mode=None, pretend=False ):
      super ( ChownChmod, self ).__init__()

      self.pretend  = bool ( pretend )
      do_chown = uid is not None or gid is not None

      self.uid      = -1 if uid is None else uid
      self.gid      = -1 if gid is None else gid

      if do_chown:
         self.chown_str = "chown {uid:d}:{gid:d} {{}}".format (
            uid=self.uid, gid=self.gid
         )
         if self.pretend:
            self.chown = self.chown_str.format
         else:
            self.chown = self._do_chown
      else:
         self.chown_str = "NO CHOWN {}"
         self.chown = self._nullfunc


      if mode is None:
         self.mode = None
      elif isinstance ( mode, str ):
         self.mode = get_stat_mode ( mode )
      else:
         self.mode = mode

      if self.mode is None:
         self.chmod_str = "NO CHMOD {}"
         self.chmod = self._nullfunc
      else:
         self.chmod_str ="chmod {mode:o} {{}}".format ( mode=self.mode )
         if self.pretend:
            self.chmod = self.chmod_str.format
         else:
            self.chmod = self._do_chmod
   # --- end of __init__ (...) ---

   def _nullfunc ( self, fspath ):
      return None

   def _do_chown ( self, fspath, _chown=_OS_CHOWN ):
      _chown ( fspath, self.uid, self.gid )
      return self.chown_str.format ( fspath )

   def _do_chmod ( self, fspath, _chmod=_OS_CHMOD ):
      _chmod ( fspath, self.mode )
      return self.chmod_str.format ( fspath )

   def chown_chmod ( self, fspath ):
      # should be renamed to chmod_chown()
      return (
         self.chmod ( fspath ),
         self.chown ( fspath )
      )
   # --- end of chown_chmod (...) ---

   def chown_chmod_recursive ( self, root ):
      chown = self.chown
      chmod = self.chmod

      if os.path.isfile ( root ):
         yield chmod ( root )
         yield chown ( root )

      else:
         for current_root, dirnames, filenames in os.walk ( root ):
            yield chmod ( current_root )
            yield chown ( current_root )

            for filename in filenames:
               fpath = current_root + os.sep + filename
               yield chmod ( fpath )
               yield chown ( fpath )
   # --- end of chown_chmod_recursive (...) ---

# --- end of ChownChmod ---


def chown_chmod ( root, uid=None, gid=None, mode=None, pretend=False ):
   return ChownChmod ( uid, gid, mode, pretend ).chown_chmod ( root )
# --- end of chown_chmod (...) ---

def chown_chmod_recursive (
   root, uid=None, gid=None, mode=None, pretend=False
):
   return ChownChmod (
      uid, gid, mode, pretend ).chown_chmod_recursive ( root )
# --- end of chown_chmod_recursive (...) ---


class AbstractFsOperations ( object ):

   PRETEND = None

   def __init__ ( self,
      stdout=None, stderr=None, uid=None, gid=None, mode=None
   ):
      if self.__class__.PRETEND is None:
         raise AssertionError ( "derived classes have to set PRETEND." )

      super ( AbstractFsOperations, self ).__init__()
      self.perm_env = ChownChmod (
         uid=uid, gid=gid, mode=mode, pretend=self.__class__.PRETEND
      )
      self._stdout = sys.stdout if stdout is None else stdout
      self._stderr = sys.stderr if stderr is None else stderr

      self.info  = self._stdout.write
      self.error = self._stderr.write
   # --- end of __init__ (...) ---

   @roverlay.util.objects.abstractmethod
   def _dodir ( self, dirpath, mkdir_p ):
      pass

   @roverlay.util.objects.abstractmethod
   def do_touch ( self, fspath ):
      pass

   @roverlay.util.objects.abstractmethod
   def chown ( self, fspath ):
      pass

   @roverlay.util.objects.abstractmethod
   def chmod ( self, fspath ):
      pass

   def chmod_chown ( self, fspath ):
      self.chmod ( fspath )
      self.chown ( fspath )

   @roverlay.util.objects.abstractmethod
   def chmod_chown_recursive ( self, root ):
      pass

   def dodir ( self, dirpath, mkdir_p=True, chown=True, chmod=True ):
      if self._dodir ( dirpath, mkdir_p=mkdir_p ):
         if chmod:
            self.chmod ( dirpath )
         if chown:
            self.chown ( dirpath )

         return True

      else:
         return False
   # --- end of dodir (...) ---

   def dodirs ( self, *dirs, **kwargs ):
      for dirpath in dirs:
         self.dodir ( dirpath, **kwargs )
   # --- end of dodirs (...) ---

   @roverlay.util.objects.abstractmethod
   def rmdir ( self, dirpath ):
      pass

   @roverlay.util.objects.abstractmethod
   def unlink ( self, fspath ):
      pass

   def wipe ( self, fspath ):
      return self.rmdir ( fspath ) or self.unlink ( fspath )

   @roverlay.util.objects.abstractmethod
   def symlink ( self, source, link_name ):
      pass

   def check_writable ( self,
      fspath, mkdir_chown=False, mkdir_chmod=False, mkdir_p=True
   ):
      """Checks whether fspath can be written. This creates all necessary
      directories."""
      success = False

      try:
         if self.do_touch ( fspath ):
            success = True

      except IOError as ioerr:
         if ioerr.errno == errno.ENOENT:
            try:
               if self.dodir (
                  os.path.dirname ( fspath ),
                  chown=mkdir_chown, chmod=mkdir_chmod, mkdir_p=mkdir_p
               ) and self.do_touch ( fspath ):
                  success = True

            except ( OSError, IOError ) as err:
               if err.errno != errno.EPERM:
                  raise

      return success
   # --- end of check_writable (...) ---

# --- end of AbstractFsOperations ---

class FsOperations ( AbstractFsOperations ):

   PRETEND = False

   def _dodir ( self, dirpath, mkdir_p ):
      return roverlay.util.common.dodir (
         dirpath, mkdir_p=mkdir_p, log_exception=False
      )
   # --- end of _dodir (...) ---

   def chmod ( self, fspath ):
      self.perm_env.chmod ( fspath )

   def chown ( self, fspath ):
      self.perm_env.chown ( fspath )

   def chmod_chown ( self, fspath ):
      self.perm_env.chown_chmod ( fspath )

   def chmod_chown_recursive ( self, root ):
      for ret in self.perm_env.chown_chmod_recursive ( root ):
         pass

   def rmdir ( self, dirpath ):
      try:
         os.rmdir ( dirpath )
      except OSError as oserr:
         return oserr.errno == errno.ENOENT
      else:
         return True
   # --- end of rmdir (...) ---

   def unlink ( self, fspath ):
      try:
         os.unlink ( fspath )
      except OSError as oserr:
         return oserr.errno == errno.ENOENT
      else:
         return True

   def symlink ( self, source, link_name ):
      try:
         os.symlink ( source, link_name )
      except OSError:
         return False
      else:
         return True

   def do_touch ( self, fspath ):
      if not os.path.lexists ( fspath ):
         with open ( fspath, 'a' ) as FH:
            pass
      return True


class VirtualFsOperations ( AbstractFsOperations ):

   PRETEND = True

   def _dodir ( self, dirpath, mkdir_p ):
      if mkdir_p:
         self.info ( "mkdir -p {!s}\n".format ( dirpath ) )
      else:
         self.info ( "mkdir {!s}\n".format ( dirpath ) )
      return True

   def chown ( self, fspath ):
      ret = self.perm_env.chown ( fspath )
      if ret is not None:
         self.info ( ret + "\n" )

   def chmod ( self, fspath ):
      ret = self.perm_env.chmod ( fspath )
      if ret is not None:
         self.info ( ret + "\n" )

   def chmod_chown_recursive ( self, root ):
      for word in self.perm_env.chmod_chown_recursive ( root ):
         if word is not None:
            self.info ( word + "\n" )

   def unlink ( self, fspath ):
      self.info ( "rm {!r}\n".format ( fspath ) )
      return True

   def rmdir ( self, dirpath ):
      self.info ( "rmdir {!r}\n".format ( dirpath ) )
      return True

   def symlink ( self, source, link_name ):
      self.info ( "ln -s {} {}\n".format ( source, link_name ) )
      return True

   def do_touch ( self, fspath ):
      self.info ( "touch {}\n".format ( fspath ) )
      return True
