# R overlay --
# -*- coding: utf-8 -*-
# Copyright (C) 2013 André Erdmann <dywi@mailerd.de>
# Distributed under the terms of the GNU General Public License;
# either version 2 of the License, or (at your option) any later version.

import abc
import errno
import functools
import itertools
import os
import pwd
import shutil
import stat
import sys

import roverlay.util.common
import roverlay.util.objects

_OS_CHOWN = getattr ( os, 'lchown', os.chown )
_OS_CHMOD = getattr ( os, 'lchmod', os.chmod )


def walk_up ( dirpath, topdown=False, max_iter=None ):
   """Generator that yields all (partial..full) filesystem paths contained
   in dirpath.

   Examples:
      walk_up (
         "/a/b/c/d", topdown=False, max_iter=None
      ) -> ( "/a/b/c/d", "/a/b/c", "/a/b", "/a", "/" )

      walk_up ( "/" ) -> ( "/" )

      walk_up ( "/b", topdown=True ) -> ( "/", "/b" )

   arguments:
   * topdown  -- Defaults to False.
   * max_iter -- max number of paths to generate (None for unlimited)
                  Defaults to None.
   """
   def iter_partial_paths ( _join_path=os.sep.join ):
      fspath        = os.path.normpath ( dirpath ).rstrip ( os.sep )
      path_elements = fspath.split ( os.sep )

      if path_elements:
         p_start = 0 if path_elements[0] else 1
         high    = len ( path_elements )

         if topdown:
            if not path_elements[0]:
               yield os.sep

            for k in range ( p_start+1, high+1 ):
               yield _join_path ( path_elements[:k] )
         else:
            for k in range ( high, p_start, -1 ):
               yield _join_path ( path_elements[:k] )

            if not path_elements[0]:
               yield os.sep
   # --- end of iter_partial_paths (...) ---

   if max_iter is None:
      for path in iter_partial_paths():
         yield path
   else:
      for n, path in enumerate ( iter_partial_paths() ):
         if n < max_iter:
            yield path
         else:
            return
# --- end of walk_up (...) ---

def get_fs_dict (
   initial_root, create_item=None, dict_cls=dict,
   dirname_filter=None, filename_filter=None,
   include_root=False, prune_empty=False, file_key=None,
):
   """Creates a dictionary-like object representing the filesystem structure
   starting at the given root directory.

   arguments:
   * initial_root    -- root directory where os.walk should start
   * create_item     -- Either a function that accepts 3 args (absolute file-
                        system path, filename, absolute dirpath) and returns
                        an object representing a file entry or None (resulting
                        in None being the object). Defaults to None.
   * dict_cls        -- dictionary class. Defaults to dict.
                         Has to have a constructor accepting an iterable
                         of 2-tuples (key,file entry or dict_cls object)
                         if create_item is set, or a .fromkeys() method
                         accepting an iterable of keys.
                         Additionally, has to provide a __setitem__ method.
   * dirname_filter  -- Either a function that returns True if a directory
                        name is allowed and False if not, or None (do not
                        restrict dirnames). Defaults to None.
                        This also affects which directory paths are traversed.
   * filename_filter -- Similar to dirname_filter, but can be used to ignore
                        files. Defaults to None.
   * include_root    -- Whether to make initial_root the dict root (False)
                        or an item in the dict (True). In other words,
                        controls whether the return value should be a dict
                        starting at initial_root or a dict containing the
                        initial_root dict. Defaults to False.
   * prune_empty     -- Whether to remove directory entries without any items.
                         Defaults to False.
   * file_key        -- Either a function that returns the dict key for a
                        file name or None (idendity, key==filename).

   Inspired by http://code.activestate.com/recipes/577879-create-a-nested-dictionary-from-oswalk/
   """
   # TODO(could-do): max_depth=N
   fsdict         = dict_cls()
   my_root        = os.path.abspath ( initial_root )

   get_file_key   = ( lambda x: x ) if file_key is None else file_key

   dictpath_begin = (
      1 + ( my_root.rfind ( os.sep ) if include_root else len ( my_root ) )
   )

   for root, dirnames, filenames in os.walk ( my_root ):
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
               parent [dictpath[-1]] = dict_cls.fromkeys (
                  map ( get_file_key, filenames )
               )
            else:
               parent [dictpath[-1]] = dict_cls (
                  (
                     get_file_key ( fname ),
                     create_item ( ( root + os.sep + fname ), fname, root )
                  )
                  for fname in filenames
               )
   # -- end for

   return fsdict
# --- end of get_fs_dict (...) ---

def create_subdir_check ( parent, fs_sep=os.sep ):
   """Returns a function that checks whether a given filesystem path is a
   subpath of parent (where parent is a subpath of itself).

   arguments:
   * parent  -- parent filesystem path for which a subdir_check should be
                created
   * fs_sep  -- defaults to os.sep
   """
   PARENT_PATH = parent.rstrip ( fs_sep ).split ( fs_sep )

   def is_subdir ( dirpath,
      _path_el=PARENT_PATH, _path_len=len( PARENT_PATH ), _fs_sep=fs_sep
   ):
      """Returns True if the given filesystem path is a subpath of the
      (predefined) parent path, else False.

      arguments:
      * dirpath   -- filesystem path to be checked
      * _path_el  -- local variable containing information about the parent
                     path. Shouldn't be set manually.
      * _path_len -- local variable containing information about the length
                     of the parent path. Shouldn't be set manually.
      * _fs_sep   -- local variable that is a copy of fs_sep.
                     Shouldn't be set manually.
      """
      dirpath_el = dirpath.rstrip ( _fs_sep ).split ( _fs_sep )
      if len ( dirpath_el ) < _path_len:
         return False
      else:
         return all (
            this == expect for this, expect in zip ( dirpath_el, _path_el )
         )
   # --- end of is_subdir (...) ---

   return is_subdir
# --- end of create_subdir_check (...) ---


def pwd_expanduser ( fspath, uid ):
   """Expands "~" in a filesystem path to the given user's home directory.
   Uses pwd to get that directory.

   Returns: expanded path

   arguments:
   * fspath --
   * uid    --
   """
   if not fspath or fspath[0] != '~':
      return fspath
   elif len ( fspath ) < 2:
      return pwd.getpwuid ( uid ).pw_dir
   elif fspath[1] == os.sep:
      return pwd.getpwuid ( uid ).pw_dir + fspath[1:]
   else:
      return fspath
# --- end of pwd_expanduser (...) ---

def walk_copy_tree ( source, dest, subdir_root=False, **walk_kwargs ):
   """Generator that iterates over the content of a filesystem tree starting
   at source and compares it to the filesystem tree starting at dest (which
   doesn't have to exist). The subdir_root can be used to control whether
   source should be a subdir of dest or not (which means that
   walk_copy_tree (source, dest, subdir_root=True) is identical to
   walk_copy_tree (source, dest + os.sep + os.path.basename(source),
   subdir_root=False)).

   The items are 6-tuples (absolute path to the source directory,
   absolute path to the dest dir, dir path relative to the source root,
   list of directories, list of files, list of dirnames).

   The dirnames list can be modified (slice assignment) in order to affect
   the directories visited by os.walk().

   The directories/files lists are lists of 2x2-tuples (
      (abspath in source, stat in source), (abspath in dest, stat in dest)
   ).

   arguments:
   * source        -- absolute path to the source root
   * dest          -- absolute path to the dest root
   * subdir_root   -- whether source should be a subdir of dest root or not
                      Defaults to False.
   * **walk_kwargs -- additional keyword arguments for os.walk()
   """
   source_path   = os.path.abspath ( source )
   dest_path     = os.path.abspath ( dest )
   relpath_begin = 1 + (
      source_path.rfind ( os.sep ) if subdir_root else len ( source_path )
   )

   get_entry = lambda path: (
      path, os.lstat ( path ) if os.path.lexists ( path ) else None
   )
   get_stat_list = lambda s, d, names: (
      [ ( get_entry ( s + name ), get_entry ( d + name ) ) for name in names ]
   )

   for root, dirnames, filenames in os.walk ( source, **walk_kwargs ):
      root_rel  = root[relpath_begin:]
      root_dest = ( dest + os.sep + root_rel if root_rel else dest )

      dirs  = get_stat_list ( root + os.sep, root_dest + os.sep, dirnames )
      files = get_stat_list ( root + os.sep, root_dest + os.sep, filenames )

      yield root, root_dest, root_rel, dirs, files, dirnames
# --- end of walk_copy_tree (...) ---

class RWX ( object ):
   """An object representing read/write/execute permissions."""

   @classmethod
   def from_str ( cls, s, strict=False ):
      """Parses the given string and returns a new RWX object.

      arguments:
      * s      -- a string, e.g. "rwx" or "r-x"
      * strict -- if True: expect that is a string with length >= 3, where
                           read/write/executable is set to True if the
                           first/second/third char is r/w/x and False
                           otherwise.
                  else   : set read/write/executable to True if s contains
                           r/w/x and False otherwise
      """
      readable, writable, executable = False, False, False

      if strict:
         _s = s.lower()
         readable   = _s[0] == 'r'
         writable   = _s[1] == 'w'
         executable = _s[2] == 'x'

      elif s:
         for char in s.lower():
            if char == 'r':
               readable   = True
            elif char == 'w':
               writable   = True
            elif char == 'x':
               executable = True
         # -- end for
      # -- end if

      return cls ( readable, writable, executable )
   # --- end of from_str (...) ---

   @classmethod
   def from_bitmask ( cls, mode, rwx_bits ):
      """Compares the given mode with a list of r/w/x bits and creates a
      RWX object for it.

      arguments:
      * mode     -- integer containing r/w/x (and possible other) bits
      * rwx_bits -- a list/tuple with at least three elements, where the
                    first/second/third element is the read/write/executable bit
      """
      return cls (
         mode & rwx_bits[0], mode & rwx_bits[1], mode & rwx_bits[2],
      )
   # --- end of from_bitmask (...) ---

   def __init__ ( self, readable, writable, executable ):
      """RWX Constructor.

      arguments:
      * readable   -- bool
      * writable   -- bool
      * executable -- bool
      """
      super ( RWX, self ).__init__()
      self.readable   = bool ( readable )
      self.writable   = bool ( writable )
      self.executable = bool ( executable )
   # --- end of __init__ (...) ---

   def __hash__ ( self ):
      # could be removed (or replaced by a more proper __hash__ func)
      return id ( self )
   # --- end of __hash__ (...) ---

   def __repr__ ( self ):
      return "<{cls.__name__}({val}) at 0x{addr:x}>".format (
         cls  = self.__class__,
         val  = self.get_str(),
         addr = id ( self ),
      )
   # --- end of __repr__ (...) ---

   def get_str ( self, fillchar='-', rwx_chars="rwx" ):
      """Returns a string similar to what ls would show ("rwx","r--",...).

      arguments:
      * fillchar  -- char that is used to express absense of read/write/exe
                     Defaults to "-".
      * rwx_chars -- a sequence of at least three chars. Defaults to "rwx."

      """
      return (
         ( rwx_chars[0] if self.readable   else fillchar ) +
         ( rwx_chars[1] if self.writable   else fillchar ) +
         ( rwx_chars[2] if self.executable else fillchar )
      )
   # --- end of get_str (...) ---

   __str__ = get_str

   def get_bitmask ( self, rwx_bits ):
      """Returns an integer representing the rwx mode for the given rwx bits.

      arguments:
      * rwx_bits -- a list/tuple with at least three elements (r,w,x)
      """
      ret = 0
      if self.readable:
         ret |= rwx_bits[0]

      if self.writable:
         ret |= rwx_bits[1]

      if self.executable:
         ret |= rwx_bits[2]

      return ret
   # --- end of get_bitmask (...) ---

# --- end of RWX ---


class FsPermissions ( object ):
   """An object representing read/write/execute permissions for users, groups
   and others."""

   USR_BITS = ( stat.S_IRUSR, stat.S_IWUSR, stat.S_IXUSR )
   GRP_BITS = ( stat.S_IRGRP, stat.S_IWGRP, stat.S_IXGRP )
   OTH_BITS = ( stat.S_IROTH, stat.S_IWOTH, stat.S_IXOTH )

   @classmethod
   def from_str ( cls, s, strict=False ):
      """Returns a new permissions object for the given string.

      arguments:
      * s      -- the string, e.g. "rwxr-x---" or "r---x---w"
      * strict -- affects how strings are parsed.
                   see RWX.from_str() for details. Defaults to False.
      """
      rwx_user   = RWX.from_str ( s[0:3], strict=strict )
      rwx_group  = RWX.from_str ( s[3:6], strict=strict )
      rwx_others = RWX.from_str ( s[6:9], strict=strict )
      return cls ( rwx_user, rwx_group, rwx_others )
   # --- end of from_str (...) ---

   @classmethod
   def from_stat_mode ( cls, stat_mode ):
      """Creates a permissions object for the given stat mode.

      arguments:
      * stat_mode -- stat mode as its returned by os.stat() (and others)
      """
      return cls (
         RWX.from_bitmask ( stat_mode, cls.USR_BITS ),
         RWX.from_bitmask ( stat_mode, cls.GRP_BITS ),
         RWX.from_bitmask ( stat_mode, cls.OTH_BITS ),
      )
   # --- end of from_stat_mode (...) ---

   def __init__ ( self, rwx_user, rwx_group, rwx_others ):
      """FsPermissions constructor.

      arguments:
      * rwx_user   -- RWX object
      * rwx_group  -- RWX object
      * rwx_others -- RWX object
      """
      super ( FsPermissions, self ).__init__()
      self.user   = rwx_user
      self.group  = rwx_group
      self.others = rwx_others
   # --- end of __init__ (...) ---

   def __repr__ ( self ):
      return "<{cls.__name__}({val}) at 0x{addr:x}>".format (
         cls  = self.__class__,
         val  = self.get_str(),
         addr = id ( self ),
      )
   # --- end of __repr__ (...) ---

   def get_str ( self, fillchar='-' ):
      """Returns an ls-like string.

      arguments:
      * fillchar -- defaults to "-"
      """
      return "".join (
         rwx.get_str ( fillchar=fillchar )
         for rwx in ( self.user, self.group, self.others )
      )
   # --- end of get_str (...) ---

   __str__ = get_str

   def get_stat_mode ( self ):
      """Returns an integer that can be used for os.[l]chmod()."""
      return (
         self.user.get_bitmask   ( self.USR_BITS ) |
         self.group.get_bitmask  ( self.GRP_BITS ) |
         self.others.get_bitmask ( self.OTH_BITS )
      )
   # --- end of get_stat_mode (...) ---

   __int__   = get_stat_mode
   __index__ = get_stat_mode

# --- end of FsPermissions ---

def get_stat_mode ( mode_str ):
   """Converts a permissions string into an integer.

   arguments:
   * mode_str -- "rwx------" etc.
   """
   return FsPermissions.from_str ( mode_str ).get_stat_mode()
# --- end of get_stat_mode (...) ---

class ChownChmod ( object ):
   """An object for chown()/chmod() operations."""
   # COULDFIX: remove / merge with AbstractFsOperations
   #            this allows to recursively chmod files and dirs

   def __init__ ( self, uid=None, gid=None, mode=None, pretend=False ):
      """ChownChmod constructor.

      arguments:
      * uid     -- uid for chown() or None (keep uid). Defaults to None.
      * gid     -- gid for chown() or None (keep gid). Defaults to None.
      * mode    -- int mode for chmod() or None (keep mode). Defaults to None.
      * pretend -- whether to actually chown/chmod (False) or just print
                   what would be done (True). Defaults to False.
      """
      super ( ChownChmod, self ).__init__()

      self.pretend  = bool ( pretend )
      do_chown = uid is not None or gid is not None

      self.uid      = -1 if uid is None else int ( uid )
      self.gid      = -1 if gid is None else int ( gid )

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
         self.mode = int ( mode )

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
      """No-op replacement for chown()/chmod().

      arguments:
      * fspath -- ignore
      """
      return None

   def _do_chown ( self, fspath, _chown=_OS_CHOWN ):
      """Calls chown(fspath)

      arguments:
      * fspath --
      """
      _chown ( fspath, self.uid, self.gid )
      return self.chown_str.format ( fspath )

   def _do_chmod ( self, fspath, _chmod=_OS_CHMOD ):
      """Calls chmod(fspath).

      arguments:
      * fspath --
      """
      _chmod ( fspath, self.mode )
      return self.chmod_str.format ( fspath )

   def chown_chmod ( self, fspath ):
      """Calls chmod(fspath) and chown(fspath).

      arguments:
      * fspath --
      """
      # should be renamed to chmod_chown()
      return (
         self.chmod ( fspath ),
         self.chown ( fspath )
      )
   # --- end of chown_chmod (...) ---

# --- end of ChownChmod ---


def chown_chmod ( fspath, uid=None, gid=None, mode=None, pretend=False ):
   """Calls chmod(fspath) and chown(fspath) after creating an intermediate
   ChownChmod instance.

   arguments:
   * fspath  --
   * uid     --
   * gid     --
   * mode    --
   * pretend --
   """
   return ChownChmod ( uid, gid, mode, pretend ).chown_chmod ( fspath )
# --- end of chown_chmod (...) ---


class AbstractFsOperations ( roverlay.util.objects.AbstractObject ):
   """Base object for performing filesystem operations."""

   @abc.abstractproperty
   def PRETEND ( self ):
      """A bool that indicates whether fs operations should be fully virtual
      (print what would be done) or not.
      Needs to be set by derived classes (as class-wide attribute).
      """
      return None

   def __init__ ( self,
      stdout=None, stderr=None, uid=None, gid=None,
      file_mode=None, dir_mode=None
   ):
      """AbstractFsOperations constructor.

      arguments:
      * stdout    -- stdout stream. Defaults to sys.stdout
      * stderr    -- stderr stream. Defaults to sys.stderr
      * uid       -- uid for chown(). Defaults to None (keep uid).
      * gid       -- gid for chown(). Defaults to None (keep gid).
      * file_mode -- mode for chmod(<file>). Defaults to None (don't change
                     mode). Can also be an ls-like str, e.g. "rwxr-x---".
      * dir_mode  -- mode for chmod(<file>). Defaults to None.
      """
      if self.__class__.PRETEND is None:
         raise AssertionError ( "derived classes have to set PRETEND." )

      super ( AbstractFsOperations, self ).__init__()
      self.perm_env_file = ChownChmod (
         uid=uid, gid=gid, mode=file_mode, pretend=self.__class__.PRETEND
      )
      self.perm_env_dir  = ChownChmod (
         uid=uid, gid=gid, mode=dir_mode, pretend=self.__class__.PRETEND
      )

      self._stdout = sys.stdout if stdout is None else stdout
      self._stderr = sys.stderr if stderr is None else stderr

      self.info  = self._stdout.write
      self.error = self._stderr.write
   # --- end of __init__ (...) ---

   @abc.abstractmethod
   def _dodir ( self, dirpath, mkdir_p ):
      """Ensures that a directory exists, by creating it if necessary.
      Also creates parent directories if mkdir_p evaluates to True.

      Returns: success (True/False)

      arguments:
      * dirpath
      * mkdir_p
      """
      return

   @abc.abstractmethod
   def do_touch ( self, fspath ):
      """Similar to "touch <fspath>".

      Returns: success (True/False)

      Raises: IOError, OSError
      """
      return

   def chown ( self, fspath ):
      """Calls chown_dir(fspath) or chown_file(fspath), depending on whether
      fspath is a directory or not.

      Returns: success (passed from chown_dir()/chown_file())

      Raises: OSError

      arguments:
      * fspath --
      """
      if os.path.isdir ( fspath ):
         return self.chown_dir ( fspath )
      else:
         return self.chown_file ( fspath )
   # --- end of chown (...) ---

   def chown_stat ( self, fspath, mode ):
      """Similar to chown(fspath), but checks the given mode in order to
      decide whether fspath is a dir.

      Returns: success (True/False)

      Raises: OSError

      arguments:
      * fspath --
      * mode   -- stat mode
      """
      if stat.S_ISDIR ( mode ):
         return self.chown_dir ( fspath )
      else:
         return self.chown_file ( fspath )
   # --- end of chown_stat (...) ---

   @abc.abstractmethod
   def chown_dir ( self, fspath ):
      """Changes the owner of a directory.

      Returns: success (True/False)

      Raises: OSError

      arguments:
      * fspath --
      """
      return

   @abc.abstractmethod
   def chown_file ( self, fspath ):
      """Changes the owner of a file.

      Returns: success (True/False)

      Raises: OSError

      arguments:
      * fspath --
      """
      return

   def chmod ( self, fspath ):
      """Calls chmod_dir(fspath) or chmod_file(fspath), depending on whether
      fspath is a directory or not.

      Returns: success (passed from chmod_dir()/chmod_file())

      Raises: OSError

      arguments:
      * fspath --
      """
      if os.path.isdir ( fspath ):
         return self.chmod_dir ( fspath )
      else:
         return self.chmod_file ( fspath )
   # --- end of chmod (...) ---

   def chmod_stat ( self, fspath, mode ):
      """Similar to chmod(fspath), but checks the given mode in order to
      decide whether fspath is a dir.

      Returns: success (True/False)

      Raises: OSError

      arguments:
      * fspath --
      * mode   -- stat mode
      """
      if stat.S_ISDIR ( mode ):
         return self.chmod_dir ( fspath )
      else:
         return self.chmod_file ( fspath )
   # --- end of chmod_stat (...) ---

   @abc.abstractmethod
   def chmod_dir ( self, fspath ):
      """Changes the mode of a directory.

      Returns: success (True/False)

      Raises: OSError

      arguments:
      * fspath --
      """
      return

   @abc.abstractmethod
   def chmod_file ( self, fspath ):
      """Changes the mode of a file.

      Returns: success (True/False)

      Raises: OSError

      arguments:
      * fspath --
      """
      return

   def chmod_chown ( self, fspath ):
      """Performs both chmod(fspath) and chown(fspath).

      Returns: 2-tuple ( chmod_success, chown_success )

      Raises: OSError

      arguments:
      * fspath --
      """
      if os.path.isdir ( fspath ):
         return (
            self.chmod_dir ( fspath ), self.chown_dir ( fspath )
         )
      else:
         return (
            self.chmod_file ( fspath ), self.chown_file ( fspath )
         )
   # --- end of chmod (...) ---

   def chmod_chown_stat ( self, fspath, mode ):
      """Similar to chmod_chown(), but checks mode in order to decide whether
      fspath is a dir.

      Returns: 2-tuple ( chmod_success, chown_success )

      Raises: OSError

      arguments:
      * fspath --
      * mode   -- stat mode
      """
      if stat.S_ISDIR ( mode ):
         return (
            self.chmod_dir ( fspath ), self.chown_dir ( fspath )
         )
      else:
         return (
            self.chmod_file ( fspath ), self.chown_file ( fspath )
         )
   # --- end of chmod_stat (...) ---

   @abc.abstractmethod
   def _copy_file ( self, source, dest ):
      """Copies a file from source to dest.

      Returns: success (True/False)

      Raises: undefined, IOError/OSError are likely

      arguments:
      * source --
      * dest   --
      """
      return
   # --- end of _copy_file (...) ---

   def copy_file ( self, source, dest, chown=True, chmod=True ):
      """Copies a file from source to dest and calls chmod(),chown()
      afterwards.

      Returns: success (True/False)

      Raises: OSError

      arguments:
      * source --
      * dest   --
      * chown  -- bool that controls whether chown() should be called.
                  Defaults to True.
      * chmod  -- bool that controls whether chmod() should be called.
                  Defaults to True.
      """
      if self._copy_file ( source, dest ):
         if chmod:
            self.chmod_file ( dest )
         if chown:
            self.chown_file ( dest )

         return True
      else:
         return False
   # --- end of copy_file (...) ---

   def dodir ( self, dirpath, mkdir_p=True, chown=True, chmod=True ):
      """Ensures that a directory exists by creating it if necessary.
      Also calls chmod(), chown() afterwards.

      Returns: success (True/False)

      Raises: OSError

      arguments:
      * dirpath --
      * mkdir_p -- whether to create parent directories as well (if necessary)
                   Defaults to True.
      * chown   -- bool that controls whether chown() should be called.
                   Defaults to True.
      * chmod   -- bool that controls whether chmod() should be called.
                   Defaults to True.
      """

      if self._dodir ( dirpath, mkdir_p=mkdir_p ):
         if chmod:
            self.chmod_dir ( dirpath )
         if chown:
            self.chown_dir ( dirpath )

         return True
      else:
         return False
   # --- end of dodir (...) ---

   def dodirs ( self, *dirs, **kwargs ):
      """Calls dodir(dir) for each dir in dirs.

      arguments:
      * *dirs    --
      * **kwargs -- keyword arguments for dodir()
      """
      for dirpath in dirs:
         self.dodir ( dirpath, **kwargs )
   # --- end of dodirs (...) ---

   @abc.abstractmethod
   def rmdir ( self, dirpath ):
      """Removes an empty directory.

      Returns: success (True/False)

      arguments:
      * dirpath --
      """
      return

   @abc.abstractmethod
   def unlink ( self, fspath ):
      """Removes a file (or link).

      Returns: success (True/False)

      arguments:
      * fspath --
      """
      return

   def wipe ( self, fspath ):
      """Removes fspath if it is an empty directory or a file (or link).

      Returns: success (True/False)

      arguments:
      * fspath --
      """
      return self.rmdir ( fspath ) or self.unlink ( fspath )

   @abc.abstractmethod
   def symlink ( self, source, link_name ):
      """Creates a symlink.

      Returns: success (True/False)

      arguments:
      * source    --
      * link_name --
      """
      return

   def check_writable ( self,
      fspath, mkdir_chown=False, mkdir_chmod=False, mkdir_p=True
   ):
      """Checks whether fspath can be written. This creates all necessary
      directories and creates fspath as empty file.

      Returns: success (True/False)

      Raises: passes IOError,OSError unless its error code is related to
              missing write permissions

      arguments:
      * fspath      --
      * mkdir_chown -- bool that controls whether created directories should
                       be chown()-ed. Defaults to False.
      * mkdir_chmod -- bool that controls whether created directories should
                       be chmod()-ed. Defaults to False.
      * mkdir_p     -- whether dodir() should create parent dirs as well.
                       Defaults to True.
      """
      success = False

      ERRNOS_IGNORE = { errno.EACCES, }

      try:
         if self.do_touch ( fspath ):
            success = True

      except IOError as ioerr:
         if ioerr.errno == errno.EPERM:
            pass
         elif ioerr.errno == errno.ENOENT:
            try:
               if self.dodir (
                  os.path.dirname ( fspath ),
                  chown=mkdir_chown, chmod=mkdir_chmod, mkdir_p=mkdir_p
               ) and self.do_touch ( fspath ):
                  success = True

            except ( OSError, IOError ) as err:
               if err.errno == errno.EPERM:
                  pass
               elif err.errno in ERRNOS_IGNORE:
                  self.error (
                     'Got {name} with unexpected '
                     'errno={code:d} ({code_name})\n'.format (
                        name      = err.__class__.__name__,
                        code      = err.errno,
                        code_name = errno.errorcode [err.errno],
                     )
                  )
               else:
                  raise
            # -- end <try again>
         elif ioerr.errno in ERRNOS_IGNORE:
            self.error (
               'Got {name} with unexpected '
               'errno={code:d} ({code_name})\n'.format (
                  name      = ioerr.__class__.__name__,
                  code      = ioerr.errno,
                  code_name = errno.errorcode [ioerr.errno],
               )
            )
         else:
            raise
      return success
   # --- end of check_writable (...) ---

   def copy_tree ( self,
      source_root, dest_root, overwrite=True, followlinks=False
   ):
      """Recursively copies files from source_root to dest_root (while keeping
      its directory structure). Ownership and permissions are not preserved,
      instead copied files and created dirs will have to permissions set
      during initialization of this object.

      Returns: None (implicit)

      arguments:
      * source_root -- directory from which files should be copied
      * dest_root   -- directory to which files should be copied
      * overwrite   -- whether to overwrite files that already exist in
                       dest_root. Defaults to True(!).
      * followlinks -- whether to follow symbolic links in os.walk().
                       Defaults to False.
      """
      dodir     = self.dodir
      copy_file = self.copy_file

      if overwrite:
         for source, dest, relpath, dirs, files, dirnames in walk_copy_tree (
            source_root, dest_root, followlinks=followlinks
         ):
            for ( source_dir, source_stat ), ( dest_dir, dest_stat ) in dirs:
               dodir ( dest_dir )

            for ( source_file, source_stat ), ( dest_file, dest_stat ) in files:
               if followlinks and stat.S_ISLINK ( source_stat ):
                  dodir ( dest_file )
               else:
                  copy_file ( source_file, dest_file )
      else:
         for source, dest, relpath, dirs, files, dirnames in walk_copy_tree (
            source_root, dest_root, followlinks=followlinks
         ):
            for ( source_dir, source_stat ), ( dest_dir, dest_stat ) in dirs:
               if dest_stat is None:
                  dodir ( dest_dir )

            for ( source_file, source_stat ), ( dest_file, dest_stat ) in files:
               if dest_stat is None:
                  if followlinks and stat.S_ISLINK ( source_stat ):
                     dodir ( dest_file )
                  else:
                     copy_file ( source_file, dest_file )
   # --- end of copy_tree (...) ---

   def copy_dirlink_tree ( self,
      source_root, dest_root, overwrite=False, followlinks=False
   ):
      """Creates symlinks to source_root's content in dest_root.

      Returns: None (implicit)

      arguments:
      * source_root --
      * dest_root   --
      * overwrite   --
      * followlinks --
      """

      unlink  = self.unlink
      symlink = self.symlink

      source, dest, relpath, dirs, files, dirnames = next (
         walk_copy_tree ( source_root, dest_root, followlinks=followlinks )
      )

      self.dodir ( dest_root )

      if overwrite:
         for ( my_source, my_source_stat ), ( my_dest, my_dest_stat ) in (
            itertools.chain ( dirs, files )
         ):
            if my_dest_stat is not None:
               unlink ( my_dest )
            symlink ( my_source, my_dest )
      else:
         for ( my_source, my_source_stat ), ( my_dest, my_dest_stat ) in (
            itertools.chain ( dirs, files )
         ):
            if my_dest_stat is None:
               symlink ( my_source, my_dest )
   # --- end of copy_dirlink_tree (...) ---

   def copy_filelink_tree ( self,
      source_root, dest_root, overwrite=False, followlinks=False
   ):
      """Like copy_tree(), but creates symlinks to files in source_root
      instead of copying them.

      arguments:
      * source_root --
      * dest_root   --
      * overwrite   --
      * followlinks --
      """
      dodir   = self.dodir
      unlink  = self.unlink
      symlink = self.symlink

      if overwrite:
         for source, dest, relpath, dirs, files, dirnames in (
            walk_copy_tree ( source_root, dest_root, followlinks=followlinks )
         ):
            for ( source_dir, source_stat ), ( dest_dir, dest_stat ) in dirs:
               dodir ( dest_dir )

            for ( source_file, source_stat ), ( dest_file, dest_stat ) in files:
               if followlinks and stat.S_ISLINK ( source_stat ):
                  dodir ( dest_file )
               else:
                  if dest_stat is not None:
                     unlink ( dest_file )
                  symlink ( source_file, dest_file )
      else:
         for source, dest, relpath, dirs, files, dirnames in (
            walk_copy_tree ( source_root, dest_root, followlinks=followlinks )
         ):
            for ( source_dir, source_stat ), ( dest_dir, dest_stat ) in dirs:
               if dest_stat is None:
                  dodir ( dest_dir )

            for ( source_file, source_stat ), ( dest_file, dest_stat ) in files:
               if dest_stat is None:
                  if followlinks and stat.S_ISLINK ( source_stat ):
                     dodir ( dest_file )
                  else:
                     symlink ( source_file, dest_file )
   # --- end of copy_filelink_tree (...) ---

# --- end of AbstractFsOperations ---


class FsOperations ( AbstractFsOperations ):

   PRETEND = False

   # this is necessary because the abstract are overridden during __init__()
   # (which doesn't get recognized by @abc.abstractmethod)
   chmod_file = None
   chown_file = None
   chmod_dir  = None
   chown_dir  = None

   def __init__ ( self, *args, **kwargs ):
      super ( FsOperations, self ).__init__ ( *args, **kwargs )
      self.chmod_file = self.perm_env_file.chmod
      self.chown_file = self.perm_env_file.chown
      self.chmod_dir  = self.perm_env_dir.chmod
      self.chown_dir  = self.perm_env_dir.chown
   # --- end of __init__ (...) ---

   def _copy_file ( self, source, dest ):
      shutil.copyfile ( source, dest )
      return True
   # --- end of _copy_file (...) ---

   def _dodir ( self, dirpath, mkdir_p ):
      return roverlay.util.common.dodir (
         dirpath, mkdir_p=mkdir_p, log_exception=False
      )
   # --- end of _dodir (...) ---

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
      except OSError as e:
         return False
      else:
         return True

   def do_touch ( self, fspath ):
      if not os.path.lexists ( fspath ):
         with open ( fspath, 'a' ) as FH:
            pass

      os.utime ( fspath, None )
      return True


class VirtualFsOperations ( AbstractFsOperations ):

   PRETEND = True

   def _copy_file ( self, source, dest ):
      self.info ( "cp {!s} {!s}\n".format ( source, dest ) )
      return True

   def _dodir ( self, dirpath, mkdir_p ):
      if mkdir_p:
         self.info ( "mkdir -p {!s}\n".format ( dirpath ) )
      else:
         self.info ( "mkdir {!s}\n".format ( dirpath ) )
      return True

   def chown_file ( self, fspath ):
      ret = self.perm_env_file.chown ( fspath )
      if ret is not None:
         self.info ( ret + "\n" )
      return True

   def chown_dir ( self, fspath ):
      ret = self.perm_env_dir.chown ( fspath )
      if ret is not None:
         self.info ( ret + "\n" )
      return True

   def chmod_file ( self, fspath ):
      ret = self.perm_env_file.chmod ( fspath )
      if ret is not None:
         self.info ( ret + "\n" )
      return True

   def chmod_dir ( self, fspath ):
      ret = self.perm_env_dir.chmod ( fspath )
      if ret is not None:
         self.info ( ret + "\n" )
      return True

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
