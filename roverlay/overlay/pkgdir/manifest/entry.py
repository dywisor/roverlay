# R overlay -- manifest package, manifest file entries
# -*- coding: utf-8 -*-
# Copyright (C) 2013 André Erdmann <dywi@mailerd.de>
# Distributed under the terms of the GNU General Public License;
# either version 2 of the License, or (at your option) any later version.

__all__ = [
   'ManifestEntry', 'PackageFileManifestEntry',
   'ManifestEntryInvalid', 'UnsupportedFileType',
]

import os.path

import roverlay.digest
import roverlay.util


class ManifestEntryInvalid ( ValueError ):
   pass

class UnsupportedFileType ( ManifestEntryInvalid ):
   pass


class ManifestEntry ( object ):
   """ManifestEntry represents a single line in the Manifest file
   '<filetype> <filename> <filesize> <chksumtypeK> <chksumK> for K in 1..N',
   where filetype is:

   * AUX    for files in the files/ directory [not used by roverlay]
   * EBUILD for all ebuilds
   * MISC   for files not directly used by ebuilds (ChangeLog, metadata.xml)
   * DIST   for release tarballs (SRC_URI)
   """

   # an ordered list of the default digest types to use
   #
   # GLEP 59:
   HASHTYPES = ( 'sha256', 'sha512', 'whirlpool', )
   #
   # old and unsupported
   ##HASHTYPES = ( 'rmd160', 'sha1', 'sha256', )

   FILETYPES = frozenset ({ 'AUX', 'EBUILD', 'MISC', 'DIST', })

   def __init__ (
      self, filetype, filepath, filename=None, filesize=None, hashes=None
   ):
      """Creates a ManifestEntry.
      Some of the data can be calculated using interpolate().

      arguments:
      * filetype  -- file type (AUX, EBUILD, MISC, DIST)
      * filepath  -- path to the file (can be None if interpolation is
                     not intended)
      * filename  -- file name
                     Defaults to None => try auto-detection.
      * filesize  -- file size, has to be an integer. Defaults to None.
      * hashes    -- a dict of checksums (sha256, ...)
                     Defaults to None.

      Required args:
      * filetype
      * filepath or (filename and filesize and hashes)
      """
      self.filetype = filetype
      self.filepath = filepath
      self.filename = filename
      self.filesize = filesize
      self.hashes   = hashes
   # --- end of __init__ (...) ---

   def add_hashes ( self, hashes ):
      """Updates the hash dict of this entry.

      arguments:
      * hashes -- hash dict that will be used to update the entry's hashdict
      """
      if self.hashes is None:
         self.hashes = dict()
      self.hashes.update ( hashes )
   # --- end of add_hashes (...) ---

   def interpolate ( self, allow_hash_create=True ):
      """
      Tries to calculate all missing data (filesize, filename and hashes).

      arguments:
      * allow_hash_create -- whether to try hash creation or not

      raises:
      * UnsupportedFileType if filetype not valid
      """
      if not self.filename:
         if (
            self.filetype == 'MISC' or
            self.filetype == 'EBUILD' or
            self.filetype == 'DIST'
         ):
            self.filename = os.path.basename ( self.filepath )
         elif self.filetype == 'AUX':
            #self.filetype = 'files' + os.path.sep + os.path.basename ( self.filepath )
            self.filetype = 'files/' + os.path.basename ( self.filepath )
         else:
            raise UnsupportedFileType ( self.filetype )
      # -- end if filename

      if allow_hash_create:
         missing_hashes = self.get_missing_hashes()
         if missing_hashes:
            self.add_hashes (
               roverlay.digest.multihash_file ( self.filepath, missing_hashes )
            )

      if not self.filesize and self.filesize != 0:
         self.filesize = roverlay.util.getsize ( self.filepath )
   # --- end of interpolate (...) ---

   def get_missing_hashes ( self ):
      """Returns an iterable of hashes that need to be calculated."""
      if not self.hashes:
         return self.HASHTYPES
      else:
         missing = set()
         for hashtype in self.HASHTYPES:
            if hashtype not in self.hashes:
               missing.add ( hashtype )
         return missing
   # --- end of get_missing_hashes (...) ---

   def __str__ ( self ):
      """Returns the string representation of this ManifestEntry
      which can directly be used in the Manifest file."""
      return "{ftype} {fname} {fsize} {hashes}".format (
         ftype=self.filetype, fname=self.filename, fsize=self.filesize,
         hashes=' '.join (
            h.upper() + ' ' + str ( self.hashes[h] ) for h in self.HASHTYPES
         )
      )
   # --- end of __str__ (...) ---

   def __repr__ ( self ):
      return "<{} for {}>".format (
         self.__class__.__name__, self.filename or self.filepath
      )
   # --- end of __repr__ (...) ---

# --- end of ManifestEntry ---

class PackageFileManifestEntry ( ManifestEntry ):
   """A ManifestEntry for package files."""

   def __init__ ( self, p_info ):
      """Constructor for PackageFileManifestEntry

      arguments:
      * p_info -- package info
      """
      pkg_file = p_info ['package_file']

      super ( PackageFileManifestEntry, self ).__init__ (
         filetype = 'DIST',
         filepath = pkg_file,
         filename = p_info ['package_src_destpath'],
         filesize = roverlay.util.getsize ( pkg_file ),
         hashes   = None,
      )

      # shared hashdict
      #   use p_info's hashdict directly
      #   (as reference, but don't modify it here!)
      self.hashes = p_info.make_hashes ( self.HASHTYPES )
   # --- end of __init__ (...) ---

   def add_hashes ( self, *args, **kwargs ):
      raise Exception (
         "add_hashes() not supported by {} due to shared hashdict!".format (
            self.__class__.__name__
         )
      )
   # --- end of add_hashes (...) ---

   def interpolate ( self, *args, **kwargs ):
      pass
   # --- end of interpolate (...) ---

# --- end of PackageFileManifestEntry ---
