# R overlay -- manifest package, manifest file creation
# -*- coding: utf-8 -*-
# Copyright (C) 2013 André Erdmann <dywi@mailerd.de>
# Distributed under the terms of the GNU General Public License;
# either version 2 of the License, or (at your option) any later version.

import os.path
import errno

import roverlay.overlay.pkgdir.manifest.entry

from roverlay.overlay.pkgdir.manifest.entry import \
   ManifestEntry, PackageFileManifestEntry

# TODO: don't write empty file(s) / remove them

class ManifestFile ( object ):
   """
   Internal implementation of the Manifest2 file creation that aims to save
   execution time (compared with calling ebuild(1)).

   The Manifest format should be in accordance with GLEP 44,
   http://www.gentoo.org/proj/en/glep/glep-0044.html.

   The used digest types are 'SHA256, SHA512, WHIRLPOOL' (GLEP 59),
   provided by hashlib (via roverlay.digest).
   """

   def __init__ ( self, root ):
      self.root     = root
      self.filepath = root + os.path.sep + 'Manifest'
      self._entries = dict()
      self.dirty    = False
   # --- end of __init__ (...) ---

   def has_entry ( self, filetype, filename ):
      return ( filetype, filename ) in self._entries
   # --- end of has_entry (...) ---

   def has_entry_search ( self, filename ):
      for k in self._entries:
         if k[1] == filename:
            return k
      return None
   # --- end of has_entry_search (...) ---

   def _add_entry ( self, new_entry ):
      """Adds an entry and marks this file as dirty.

      arguments:
      * new_entry -- entry to add
      """
      self._entries [ ( new_entry.filetype, new_entry.filename ) ] = new_entry
      self.dirty = True
   # --- end of _add_entry (...) ---

   def add_entry ( self, filetype, filepath, filename=None ):
      """Adds an entry for the given file.

      arguments:
      * filetype -- AUX, EBUILD, DIST, MISC
      * filepath -- path to the file
      * filename -- (optional) name of the file
      """
      new_entry = ManifestEntry ( filetype, filepath, filename )
      new_entry.interpolate()
      self._add_entry ( new_entry )
   # --- end of add_entry (...) ---

   def add_metadata_entry ( self, ignore_missing=False ):
      """Adds an entry for metadata.xml.

      arguments:
      * ignore_missing -- check whether metadata.xml actually exists and
                          don't add an entry if not

      Note: any existing metadata.xml entry will be removed
      """
      fname = 'metadata.xml'
      fpath = self.root + os.path.sep + fname
      if not ignore_missing or os.path.exists ( fpath ):
         self.add_entry ( 'MISC', fpath, fname )
         return True
      else:
         try:
            del self._entries [ ( 'MISC', fname ) ]
         except KeyError:
            pass
         else:
            self.dirty = True
         return False
   # --- end of add_metadata_entry (...) ---

   def add_package_entry ( self, p_info, add_ebuild=True ):
      """Adds an entry for the package file of a package info object, and
      optionally for its ebuild, too.

      arguments:
      * p_info     -- package info
      * add_ebuild -- if True: add an entry for p_info's ebuild
                      Defaults to True.

      Note: This method can only be used for "new" package infos.
      """
      p_entry = PackageFileManifestEntry ( p_info )

      if add_ebuild:
         efile = p_info ['ebuild_file']
         if efile is None:
            raise Exception ( "ebuild file must exist." )
         e_entry = ManifestEntry ( 'EBUILD', efile )
         e_entry.interpolate()

         self._add_entry ( e_entry )

      self._add_entry ( p_entry )
   # --- end of add_package_entry (...) ---

   def remove_entry ( self, filetype, filename ):
      """Removes an entry.

      arguments:
      * filetype -- the entry's filetype
      * filename -- the entry's filename
      """
      del self._entries [ ( filetype, filename ) ]
      self.dirty = True
   # --- end of remove_entry (...) ---

   def remove_metadata_entry ( self ):
      """Removes the metadata.xml entry."""
      self.remove_entry ( 'MISC', 'metadata.xml' )
   # --- end of remove_metadata_entry (...) ---

   def remove_package_entry ( self, p_info, with_ebuild=True ):
      """Removes a package entry (and optionally its ebuild entry).

      arguments:
      * p_info      -- package info
      * with_ebuild -- whether to remove the ebuild entry (defaults to True)
      """
      filename = p_info.get ( 'package_src_destpath', do_fallback=True )

      if with_ebuild:
         efile = p_info.get ( 'ebuild_file' )
         if not efile:
            raise Exception ( "package info object has no ebuild file" )
         self.remove_entry ( 'EBUILD', os.path.basename ( efile ) )

      self.remove_entry ( 'DIST', filename )
   # --- end of remove_package_entry (...) ---

   def read ( self, update=False, ignore_missing=False ):
      """Reads and imports the Manifest file.

      arguments:
      * update         -- if True: add non-existing entries only
                          Defaults to False.
      * ignore_missing -- if True: don't raise an exception if the Manifest
                          file does not exist. Defaults to False.
      """
      FILETYPES = ManifestEntry.FILETYPES
      HASHTYPES = ManifestEntry.HASHTYPES

      FH = None
      try:
         FH = open ( self.filepath, 'rt' )

         for line in FH.readlines():
            rsline = line.rstrip()
            if rsline:
               #<filetype> <filename> <filesize> <hashes...>
               lc = rsline.split ( None )
               if lc[0] in FILETYPES:
                  # expect uneven number of line components (3 + <hash pairs>)
                  assert len ( lc ) % 2 == 1 and len ( lc ) > 3

                  filetype  = lc[0]
                  filename  = lc[1]
                  key = ( filetype, filename )

                  if not update or key not in self._entries:
                     filesize  = lc[2]
                     hashes    = dict()
                     hash_name = None
                     for word in lc[3:]:
                        if hash_name is None:
                           hash_name = word.lower()
                        else:
                           hashes [hash_name] = word
                           # ^ = int ( word, 16 )
                           hash_name = None
                     # -- end for;

                     self._entries [ ( filetype, filename ) ] = (
                        ManifestEntry (
                           filetype, None, filename, filesize, hashes
                        )
                     )
                  # -- end if not update or new
               # else ignore

      except IOError as ioerr:
         if ignore_missing and ioerr.errno == errno.ENOENT:
            pass
         else:
            raise
      finally:
         if FH:
            FH.close()
   # --- end of read (...) ---

   def gen_lines ( self, do_sort=True ):
      """Generates text file lines.

      arguments:
      * do_sort -- if True: produce sorted output (defaults to True)
      """
      if do_sort:
         for item in sorted ( self._entries.items(), key=lambda kv: kv[0] ):
            yield str ( item[1] )
      else:
         for entry in self._entries.values():
            yield str ( entry )
   # --- end of gen_lines (...) ---

   def __str__ ( self ):
      return '\n'.join ( self.gen_lines() )
   # --- end of __str__ (...) ---

   def __repr__ ( self ):
      # COULDFIX: very efficient!
      return "<Manifest for {}>".format (
         os.path.sep.join ( self.root.rsplit ( os.path.sep, 2 ) [-2:] )
      )
   # --- end of __repr__ (...) ---

   def write ( self, force=False ):
      """Writes the Manifest file.

      arguments:
      * force -- enforce writing even if no changes made
      """
      if force or self.dirty:
         with open ( self.filepath, 'wt' ) as FH:
            for line in self.gen_lines():
               FH.write ( line )
               FH.write ( '\n' )

         self.dirty = False
         return True
      else:
         return False
   # --- end of write (...) ---

   def exists ( self ):
      """Returns True if the Manifest file exists (as file), else False."""
      return os.path.isfile ( self.filepath )
   # --- end of exists (...) ---

# --- end of ManifestFile ---
