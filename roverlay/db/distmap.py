# R overlay -- db, ( dist file ) => ( repo, repo file ) map
# -*- coding: utf-8 -*-
# Copyright (C) 2013 André Erdmann <dywi@mailerd.de>
# Distributed under the terms of the GNU General Public License;
# either version 2 of the License, or (at your option) any later version.

import errno

import bz2
import gzip

import os.path
import shutil


import roverlay.digest
import roverlay.util
import roverlay.stats.collector


__all__ = [ 'DistMapInfo', 'get_distmap' ]

#COULDFIX: distmap could use roverlay.util.fileio


class DistMapInfo ( object ):
   """Distmap entry"""

   DIGEST_TYPE           = 'sha256'
   RESTORE_FROM_DISTFILE = '_'
   UNSET                 = 'U'

   def __init__ ( self, distfile, repo_name, repo_file, sha256 ):
      """Distmap entry constructor.

      arguments:
      * distfile  -- distfile path relative to the distroot
      * repo_name -- name of the repo that owns the package file
      * repo_file -- path of the package file relative to the repo
      * sha256    -- file checksum
      """
      super ( DistMapInfo, self ).__init__()

      self.repo_name = repo_name if repo_name is not None else self.UNSET
      self.sha256    = sha256

      if repo_file == self.RESTORE_FROM_DISTFILE:
         self.repo_file = distfile
      else:
         self.repo_file = repo_file if repo_file is not None else self.UNSET
   # --- end of __init__ (...) ---

   @property
   def digest ( self ):
      return self.sha256
      #return getattr ( self, self.DIGEST_TYPE )
   # --- end of digest (...) ---

   def compare_digest ( self, package_info ):
      p_hash = package_info.make_distmap_hash()
      return ( bool ( p_hash == self.digest ), p_hash )
   # --- end of compare_digest (...) ---

   def __eq__ ( self, other ):
      if isinstance ( other, DistMapInfo ):
         return (
            self.sha256        == other.sha256
            and self.repo_name == other.repo_name
            and self.repo_file == other.repo_file
         )
      else:
         return super ( DistMapInfo, self ).__ne__ ( other )
   # --- end of __eq__ (...) ---

   def __ne__ ( self, other ):
      if isinstance ( other, DistMapInfo ):
         return (
            self.sha256       != other.sha256
            or self.repo_name != other.repo_name
            or self.repo_file != other.repo_file
         )
      else:
         return super ( DistMapInfo, self ).__ne__ ( other )
   # --- end of __ne__ (...) ---

   def to_str ( self, distfile, field_delimiter ):
      """Returns a distmap string.

      arguments:
      * distfile        --
      * field_delimiter -- char (or char sequence) that is used to separate
                           values
      """
      return ( field_delimiter.join ((
         distfile,
         self.repo_name,
         (
            self.RESTORE_FROM_DISTFILE if self.repo_file == distfile
            else self.repo_file
         ),
         self.sha256
      )) )
   # --- end of to_str (...) ---

# --- end of DistMapInfo ---


def get_distmap ( distmap_file, distmap_compression, ignore_missing=False ):
   """Returns a new distmap instance.

   arguments:
   * distmap_file        -- file with distmap info entries
   * distmap_compression -- distmap file compression format (None: disable)
   * ignore_missing      -- do not fail if distmap file does not exist?

   raises: ValueError if distmap_compression not supported.
   """
   if not distmap_compression or (
      distmap_compression in { 'default', 'none' }
   ):
      return FileDistMap (
         distmap_file, ignore_missing=ignore_missing
      )
   elif distmap_compression in { 'bz2', 'bzip2' }:
      return Bzip2CompressedFileDistMap (
         distmap_file, ignore_missing=ignore_missing
      )
   elif distmap_compression in { 'gz', 'gzip' }:
      return GzipCompressedFileDistMap (
         distmap_file, ignore_missing=ignore_missing
      )
   else:
      raise ValueError (
         "unknown distmap_compression {!r}".format ( distmap_compression )
      )
# --- end of get_distmap (...) ---


class _DistMapBase ( object ):

   # { attr[, as_attr] }
   DISTMAP_BIND_ATTR = frozenset ({ 'get', 'keys', 'items', 'values', })

   class AbstractMethod ( NotImplementedError ):
      pass
   # --- end of AbstractMethod ---

   def __init__ ( self ):
      super ( _DistMapBase, self ).__init__()
      self.dirty    = False
      self._distmap = dict()
      self.stats    = roverlay.stats.collector.static.distmap

      self._rebind_distmap()

      self.update_only = True
   # --- end of __init__ (...) ---

   def __getitem__ ( self, key ):
      return self._distmap [key]
   # --- end of __getitem__ (...) ---

   def __iter__ ( self ):
      return iter ( self._distmap )
   # --- end of __iter__ (...) ---

   def __len__ ( self ):
      return len ( self._distmap )
   # --- end of __len__ (...) ---

   def __bool__ ( self ):
      return True
   # --- end of __bool__ (...) ---

   def __setitem__ ( self, key, value ):
      if isinstance ( value, DistMapInfo ):
         self.add_entry ( key, value )
      elif hasattr ( value, 'get_distmap_value' ):
         self.add_entry (
            key, DistMapInfo ( key, *value.get_distmap_value() )
         )
      else:
         self.add_entry ( key, DistMapInfo ( key, *value ) )
   # --- end of __setitem__ (...) ---

   def _nondirty_file_added ( self, distfile ):
      self.stats.file_added()
   # --- end of _nondirty_file_added (...) ---

   def _file_added ( self, distfile ):
      self.stats.file_added()
      self.dirty = True
   # --- end of _file_added (...) ---

   def _file_removed ( self, distfile ):
      self.stats.file_removed()
      self.dirty = True
   # --- end of _file_removed (...) ---

   def _rebind_distmap ( self ):
      for attr in self.DISTMAP_BIND_ATTR:
         if isinstance ( attr, str ):
            setattr ( self, attr, getattr ( self._distmap, attr ) )
         else:
            setattr ( self, attr [1], getattr ( self._distmap, attr[0] ) )
   # --- end of _rebind_distmap (...) ---

   def check_revbump_necessary ( self, package_info ):
      """Tries to find package_info's distfile in the distmap and returns
      whether a revbump is necessary (True) or not (False).

      Compares checksums if distfile already exists.

      arguments:
      * package_info --
      """
      distfile = package_info.get_distmap_key()

      info = self._distmap.get ( distfile, None )
      if info is None:
         # new file, no revbump required
         return False
      elif info.repo_name != package_info['origin'].name:
         # don't revbump if repo names don't match, this likely results in
         # infinite revbumps if a package is available from more than one repo
         return False
      elif info.compare_digest ( package_info ) [0] is True:
         # old digest == new digest, no revbump
         #  (package_info should be filtered out)
         return False
      else:
         # digest mismatch => diff
         return True
   # --- end of compare_digest (...) ---

   def get_hash_type ( self ):
      return DistMapInfo.DIGEST_TYPE
   # --- end of get_hash_types (...) ---

   def get_file_digest ( self, f ):
      """Returns a file checksum for the given file.

      arguments:
      * f --
      """
      return roverlay.digest.dodigest_file ( f, DistMapInfo.DIGEST_TYPE )
   # --- end of get_file_digest (...) ---

   def check_digest_integrity ( self, distfile, digest ):
      info = self._distmap.get ( distfile, None )

      if info is None:
         # file not found
         return 1
      elif info.digest == digest:
         # file OK
         return 0
      else:
         # bad checksum
         return 2
   # --- end of check_digest_integrity (...) ---

   def check_integrity ( self, distfile, distfilepath ):
      """Verifies a distfile by comparing its filepath with the distmap entry.
      Returns 1 if the file is not in the distmap, 2 if the file's checksum
      differs and 0 if the file is ok.

      arguments:
      * distfile     -- distfile path relative to the distroot
      * distfilepath -- absolute path to the distfile
      """
      if self._distmap.get ( distfile, None ) is None:
         return 1
      else:
         return self.check_digest_integrity (
            distfile, self.get_file_digest ( distfilepath )
         )
   # --- end of check_integrity (...) ---

   def remove ( self, key ):
      """Removes an entry from the distmap.

      arguments:
      * key -- distfile path relative to the distroot
      """
      del self._distmap [key]
      self._file_removed ( key )
   # --- end of remove (...) ---

   def try_remove ( self, key ):
      """Tries to remove an entry from the distfile.
      Does nothing if no entry found.

      arguments:
      * key -- distfile path relative to the distroot
      """
      try:
         del self._distmap [key]
         self._file_removed ( key )
      except KeyError:
         pass
   # --- end of try_remove (...) ---

   def make_reverse_distmap ( self ):
      """Creates a reverse distmap that can be used to find repo files in the
      distdir.

      The reverse distmap has to be recreated after modifying the original
      distmap.
      """
      self._reverse_distmap = {
         ( kv[1].repo_name, kv[1].repo_file ): kv
            for kv in self._distmap.items()
      }
      return self._reverse_distmap
   # --- end of make_reverse_distmap (...) ---

   def release_reverse_distmap ( self ):
      """Removes the cached reverse distmap."""
      try:
         del self._reverse_distmap
      except AttributeError:
         pass
   # --- end of release_reverse_distmap (...) ---

   def lookup ( self, repo_name, repo_file ):
      """Tries to find a repo file in distroot.
      Returns a 2-tuple ( <relative distfile path>, <distmap entry> ) if
      repo file found, else None.

      Note: Creating a reverse distmap allows faster lookups.

      arguments:
      * repo_name -- name of the repo that owns repo_file
      * repo_file -- repo file (relative to repo directory)
      """
      if hasattr ( self, '_reverse_distmap' ):
         return self._reverse_distmap.get ( ( repo_name, repo_file ), None )
      else:
         for distfile, info in self._distmap.items():
            if info.repo_name == repo_name and info.repo_file == repo_file:
               return ( distfile, info )
            # -- end if
         else:
            return None
   # --- end of lookup (...) ---

   def add_entry ( self, distfile, distmap_info ):
      """Adds an entry to the distmap.

      arguments:
      * distfile     -- distfile path relative to the distroot
      * distmap_info -- distmap entry
      """
      if self.update_only:
         entry = self._distmap.get ( distfile, None )
         if entry is None or entry != distmap_info:
            self._distmap [distfile] = distmap_info
            self._file_added ( distfile )
            del entry
      else:
         self._distmap [distfile] = distmap_info
         self._file_added ( distfile )

      return True
   # --- end of add_entry (...) ---

   def add_entry_for ( self, p_info ):
      """Creates and adds an entry for a PackageInfo instance to the distmap.

      arguments:
      * p_info --
      """
      key = p_info.get_distmap_key()
      return self.add_entry (
         key, DistMapInfo ( key, *p_info.get_distmap_value() )
      )
   # --- end of add_entry_for (...) ---

   def add_dummy_entry ( self, distfile, distfilepath=None, hashdict=None ):
      """Adds a dummy entry.
      Such an entry contains a checksum and a distfile, but no information
      about its origin (repo name/file).

      arguments:
      * distfile     -- distfile path relative to the distroot
      * distfilepath -- absolute path to the distfile
      * hashdict     -- dict with already calculated hashes
      """
      if hashdict and DistMapInfo.DIGEST_TYPE in hashdict:
         digest = hashdict [DistMapInfo.DIGEST_TYPE]
      else:
         digest = self.get_file_digest ( distfilepath )

      return self.add_entry (
         distfile, DistMapInfo ( distfile, None, None, digest )
      )
   # --- end of add_dummy_entry (...) ---

# --- end of _DistMapBase ---


class _FileDistMapBase ( _DistMapBase ):
   """A distmap that is read from / written to a file."""

   # the default info field separator
   FIELD_DELIMITER = '|'
   #FIELD_DELIMITER = ' '

   # file format (reserved for future usage)
   FILE_FORMAT = '0'

   def __init__ ( self, filepath, ignore_missing=False ):
      super ( _FileDistMapBase, self ).__init__ ()
      self.dbfile = filepath
      if ignore_missing:
         self.try_read()
      else:
         self.read()
   # --- end of __init__ (...) ---

   def backup_file ( self, destfile=None, move=False, ignore_missing=False ):
      """Creates a backup copy of the distmap file.

      arguments:
      * destfile       -- backup file path
                          Defaults to <distmap file> + '.bak'.
      * move           -- move distmap file (instead of copying)
      * ignore_missing -- return False if distmap file does not exist instead
                          of raising an exception
                          Defaults to False.
      """
      dest = destfile or self.dbfile + '.bak'
      try:
         roverlay.util.dodir ( os.path.dirname ( dest ), mkdir_p=True )
         if move:
            shutil.move ( self.dbfile, dest )
            return True
         else:
            shutil.copyfile ( self.dbfile, dest )
            return True
      except IOError as ioerr:
         if ignore_missing and ioerr.errno == errno.ENOENT:
            return False
         else:
            raise
   # --- end of backup_file (...) ---

   def backup_and_write ( self,
      db_file=None, backup_file=None,
      force=False, move=False, ignore_missing=True
   ):
      """Creates a backup copy of the distmap file and writes the modified
      distmap afterwards.

      arguments:
      * db_file        -- distmap file path (defaults to self.dbfile)
      * backup_file    -- backup file path (see backup_file())
      * force          -- enforce writing even if distmap not modified
      * move           -- move distmap (see backup_file())
      * ignore_missing -- do not fail if distmap file does not exist
                          Defaults to True.
      """
      if force or self.dirty:
         self.backup_file (
            destfile=backup_file, move=move, ignore_missing=ignore_missing
         )
         return self.write ( filepath=db_file, force=True )
      else:
         return True
   # --- end of backup_and_write (...) ---

   def file_exists ( self ):
      """Returns True if the distmap file exists, else False."""
      return os.path.isfile ( self.dbfile )
   # --- end of file_exists (...) ---

   def try_read ( self, *args, **kwargs ):
      """Tries to read the distmap file."""
      try:
         self.read ( *args, **kwargs )
      except IOError as ioerr:
         if ioerr.errno == errno.ENOENT:
            pass
         else:
            raise
   # --- end of try_read (...) ---

   def _file_written ( self, filepath ):
      """Method that should be called after writing a distmap file."""
      self.dirty = self.dirty and ( filepath is not self.dbfile )
   # --- end of _file_written (...) ---

   def _file_read ( self, filepath ):
      """Method that should be called after reading a distmap file."""
      self.dirty = self.dirty or ( filepath is not self.dbfile )
   # --- end of _file_read (...) ---

   def gen_lines ( self ):
      """Generator that creates distmap file text lines."""
      # header
      yield "<{d}<{fmt}".format (
         d=self.FIELD_DELIMITER, fmt=self.FILE_FORMAT
      )
      for distfile, info in self._distmap.items():
         yield info.to_str ( str ( distfile ), self.FIELD_DELIMITER )
   # --- end of gen_lines (...) ---

   def _read_header ( self, line ):
      """Tries to parse a text line as distmap file header.
      Returns True if line was a header line, else False.

      arguments:
      * line --
      """
      if len ( line ) > 2 and line[0] == line[2]:
         # instance attr
         self.FIELD_DELIMITER = line[1]
         if len ( line ) > 3:
            self.FILE_FORMAT = line[3:]
         return True
      else:
         return False
   # --- end of _read_header (...) ---

   def read ( self, filepath=None ):
      """Reads the distmap.

      arguments:
      * filepath -- path to the distmap file (defaults to self.dbfile)
      """
      raise self.__class__.AbstractMethod()
   # --- end of read (...) ---

   def write ( self, filepath=None, force=False ):
      """Writes the distmap.

      arguments:
      * filepath -- path to the distmap file (defaults to self.dbfile)
      * force    -- enforce writing even if distmap not modified
      """
      raise self.__class__.AbstractMethod()
   # --- end of write (...) ---

# --- end of _FileDistMapBase ---


class FileDistMap ( _FileDistMapBase ):

   def read ( self, filepath=None ):
      f     = filepath or self.dbfile
      first = True
      with open ( f, 'rt') as FH:
         for line in FH.readlines():
            rsline = line.rstrip('\n')

            if first:
               first = False
               if self._read_header ( rsline ):
                  continue
               # else no header
            # -- end if

            distfile, info = roverlay.util.headtail (
               rsline.split ( self.FIELD_DELIMITER )
            )
            self._distmap [distfile] = DistMapInfo ( distfile, *info )
            self._nondirty_file_added ( distfile )
         # -- end for
         self._file_read ( f )
   # --- end of read_file (...) ---

   def write ( self, filepath=None, force=False ):
      if force or self.dirty:
         f  = filepath or self.dbfile
         roverlay.util.dodir ( os.path.dirname ( f ), mkdir_p=True )
         with open ( f, 'wt' ) as FH:
            for line in self.gen_lines():
               FH.write ( line )
               FH.write ( '\n' )
            self._file_written ( f )
         return True
      else:
         return False
   # --- end of write (...) ---

# --- end of FileDistMap ---

class _CompressedFileDistMap ( _FileDistMapBase ):

   # _OPEN_COMPRESSED:
   #  callable that returns a file handle for reading compressed files
   #
   _OPEN_COMPRESSED = None

   def read ( self, filepath=None ):
      f     = filepath or self.dbfile
      first = True
      with self._OPEN_COMPRESSED ( f, mode='r' ) as FH:
         for compressed in FH.readlines():
            rsline = compressed.decode().rstrip('\n')

            if first:
               first = False
               if self._read_header ( rsline ):
                  continue
               # else no header
            # -- end if

            distfile, info = roverlay.util.headtail (
               rsline.split ( self.FIELD_DELIMITER )
            )
            self._distmap [distfile] = DistMapInfo ( distfile, *info )
            self._nondirty_file_added ( distfile )
         # -- end for
         self._file_read ( f )
   # --- end of read (...) ---

   def write ( self, filepath=None, force=False ):
      if force or self.dirty:
         f  = filepath or self.dbfile
         nl = '\n'.encode()
         roverlay.util.dodir ( os.path.dirname ( f ), mkdir_p=True )
         with self._OPEN_COMPRESSED ( f, mode='w' ) as FH:
            for line in self.gen_lines():
               FH.write ( line.encode() )
               FH.write ( nl )
            self._file_written ( f )
         return True
      else:
         return False
   # --- end of write (...) ---

# --- end of _CompressedFileDistMap ---

def create_CompressedFileDistMap ( open_compressed ):
   """Creates a CompressedFileDistMap class.

   arguments:
   * open_compressed -- function that returns a file handle for reading
   """
   class CompressedFileDistMap ( _CompressedFileDistMap ):
      _OPEN_COMPRESSED = open_compressed
   # --- end of CompressedFileDistMap ---
   return CompressedFileDistMap
# --- end of create_CompressedFileDistMap (...) ---

# bzip2, gzip
Bzip2CompressedFileDistMap = create_CompressedFileDistMap ( bz2.BZ2File )
GzipCompressedFileDistMap  = create_CompressedFileDistMap ( gzip.GzipFile )
