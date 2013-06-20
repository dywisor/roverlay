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


__all__ = [ 'DistMapInfo', 'get_distmap' ]


class DistMapInfo ( object ):

   DIGEST_TYPE           = 'sha256'
   RESTORE_FROM_DISTFILE = '_'
   UNSET                 = 'U'

   def __init__ ( self, distfile, repo_name, repo_file, sha256 ):
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
      return not self.__ne__ ( other )
   # --- end of __eq__ (...) ---

   def __ne__ ( self, other ):
      if isinstance ( other, DistMapInfo ):
         return (
            self.sha256 != other.sha256
            or self.repo_name != other.repo_name
            or self.repo_file != other.repo_file
         )
      else:
         return super ( DistMapInfo, self ).__ne__ ( other )
   # --- end of __ne__ (...) ---

   def to_str ( self, distfile, d ):
      return ( d.join ((
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
      elif info.compare_digest ( package_info ) [0] is True:
         # old digest == new digest, no revbump
         #  (package_info should be filtered out)
         return False
      else:
         # digest mismatch => diff
         return True
   # --- end of compare_digest (...) ---

   def get_file_digest ( self, f ):
      return roverlay.digest.dodigest_file ( f, DistMapInfo.DIGEST_TYPE )
   # --- end of get_file_digest (...) ---

   def check_integrity ( self, distfile, distfilepath ):
      info = self._distmap.get ( distfile, None )

      if info is None:
         # file not found
         return 1
      elif info.digest == self.get_file_digest ( distfilepath ):
         # file OK
         return 0
      else:
         # bad checksum
         return 2
   # --- end of check_integrity (...) ---

   def remove ( self, key ):
      del self._distmap [key]
      self.dirty = True
   # --- end of remove (...) ---

   def try_remove ( self, key ):
      try:
         del self._distmap [key]
         self.dirty = True
      except KeyError:
         pass
   # --- end of try_remove (...) ---

   def make_reverse_distmap ( self ):
      self._reverse_distmap = {
         ( kv[1].repo_name, kv[1].repo_file ): kv
            for kv in self._distmap.items()
      }
   # --- end of make_reverse_distmap (...) ---

   def release_reverse_distmap ( self ):
      try:
         del self._reverse_distmap
      except AttributeError:
         pass
   # --- end of release_reverse_distmap (...) ---

   def lookup ( self, repo_name, repo_file ):
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
      if self.update_only:
         entry = self._distmap.get ( distfile, None )
         if entry is None or entry != distmap_info:
            self._distmap [distfile] = distmap_info
            self.dirty = True
            del entry
      else:
         self._distmap [distfile] = distmap_info
         self.dirty = True

      return True
   # --- end of add_entry (...) ---

   def add_entry_for ( self, p_info ):
      key = p_info.get_distmap_key()
      return self.add_entry (
         key, DistMapInfo ( key, *p_info.get_distmap_value() )
      )
   # --- end of add_entry_for (...) ---

   def add_dummy_entry ( self, distfile, distfilepath ):
      print ( "DUMMY", distfile )
      return self.add_entry (
         distfile,
         DistMapInfo (
            distfile, None, None, self.get_file_digest ( distfilepath ),
         )
      )
   # --- end of add_dummy_entry (...) ---

   def read ( self, *args, **kwargs ):
      raise self.__class__.AbstractMethod()
   # --- end of read (...) ---

   def write ( self, *args, **kwargs ):
      raise self.__class__.AbstractMethod()
   # --- end of write (...) ---


# --- end of _DistMapBase ---


class _FileDistMapBase ( _DistMapBase ):

   FIELD_DELIMITER = '|'
   #FIELD_DELIMITER = ' '
   FILE_FORMAT     = '0'

   def __init__ ( self, filepath, ignore_missing=False ):
      super ( _FileDistMapBase, self ).__init__ ()
      self.dbfile = filepath
      if ignore_missing:
         self.try_read()
      else:
         self.read()
   # --- end of __init__ (...) ---

   def backup_file ( self, destfile=None, move=False, ignore_missing=False ):
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

   def file_exists ( self ):
      return os.path.isfile ( self.dbfile )
   # --- end of file_exists (...) ---

   def try_read ( self, *args, **kwargs ):
      try:
         self.read()
      except IOError as ioerr:
         if ioerr.errno == errno.ENOENT:
            pass
         else:
            raise
   # --- end of try_read (...) ---

   def _file_written ( self, filepath ):
      self.dirty = self.dirty and ( filepath is not self.dbfile )
   # --- end of _file_written (...) ---

   def _file_read ( self, filepath ):
      self.dirty = self.dirty or ( filepath is not self.dbfile )
   # --- end of _file_read (...) ---

   def gen_lines ( self ):
      # header
      yield "<{d}<{fmt}".format (
         d=self.FIELD_DELIMITER, fmt=self.FILE_FORMAT
      )
      for distfile, info in self._distmap.items():
         yield (
            str ( distfile ) + self.FIELD_DELIMITER
            + info.to_str ( distfile, self.FIELD_DELIMITER )
         )
   # --- end of gen_lines (...) ---

   def _read_header ( self, line ):
      if len ( line ) > 2 and line[0] == line[2]:
         # instance attr
         self.FIELD_DELIMITER = line[1]
         if len ( line ) > 3:
            self.FILE_FORMAT = line[3:]
         return True
      else:
         return False
   # --- end of _read_header (...) ---

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
         self._file_read ( f )
   # --- end of read_file (...) ---

   def write ( self, filepath=None, force=False ):
      if force or self.dirty:
         print ( "DBFILE WILL BE WRITTEN", force, dirty, list(self.keys()) )
         f  = filepath or self.dbfile
         roverlay.util.dodir ( os.path.dirname ( f ), mkdir_p=True )
         with open ( f, 'wt' ) as FH:
            for line in self.gen_lines():
               FH.write ( line )
               FH.write ( '\n' )
            self._file_written ( f )
         return True
      else:
         print ( "DBFILE WILL NOT BE WRITTEN", force, dirty, list(self.keys()) )
         return False
   # --- end of write (...) ---

# --- end of FileDistMap ---

class _CompressedFileDistMap ( _FileDistMapBase ):

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
   class CompressedFileDistMap ( _CompressedFileDistMap ):
      _OPEN_COMPRESSED = open_compressed
   # --- end of CompressedFileDistMap ---
   return CompressedFileDistMap
# --- end of create_CompressedFileDistMap (...) ---

Bzip2CompressedFileDistMap = create_CompressedFileDistMap ( bz2.BZ2File )
GzipCompressedFileDistMap  = create_CompressedFileDistMap ( gzip.GzipFile )
