# R overlay -- metadata package (__init__)
# -*- coding: utf-8 -*-
# Copyright (C) 2012 André Erdmann <dywi@mailerd.de>
# Distributed under the terms of the GNU General Public License;
# either version 2 of the License, or (at your option) any later version.

"""metadata package

This package implements metadata creation for PackageInfo instances,
and this module provides the MetadataJob class that can be used in PackageDir
instances to create and write a metadata.xml file.
"""

__all__ = [ 'MetadataJob', ]

import roverlay.config

from roverlay.overlay.pkgdir.metadata import nodes

USE_FULL_DESCRIPTION = True

class MetadataJob ( object ):
   """R package description data -> metadata.xml interface."""

   METADATA_SUCCESS     = 0
   METADATA_NO_PACKAGE  = 2**0
   METADATA_EMPTY       = 2**1
   METADATA_WRITE_ERROR = 2**2

   DATA_KEYS = frozenset ({ 'Description', 'Title' })

   def __init__ ( self, filepath, logger ):
      """Initializes a MetadataJob.

      arguments:
      * filepath -- path where the metadata file will be written to
      * logger   -- parent logger to use
      """
      self.logger          = logger.getChild ( 'metadata' )
      self._package_info   = None
      self.filepath        = filepath
      self.last_write_code = -1

      # no longer storing self._metadata, which will only be created twice
      # when running show() (expected 1x write per PackageInfo instance)
   # --- end of __init__ (...) ---

   def empty ( self ):
      return self._package_info is None
   # --- end of empty (...) ---

   def update ( self, package_info ):
      """Updates the metadata.
      Actually, this won't create any metadata, it will only set the
      PackageInfo object to be used for metadata creation.

      arguments:
      * package_info --
      """

      if package_info.compare_version ( self._package_info ) > 0:
         desc_data = package_info.get (
            'desc_data', fallback_value=None, do_fallback=True
         )
         if desc_data and any (
            desc_data.get ( key, None ) for key in self.DATA_KEYS
         ):
            # another solution would be to merge data from several
            # PackageInfo instances (while preferring pkgs with higher
            # versions), doesn't make sense for one metadata field, though
            self._package_info = package_info
   # --- end of update (...) ---

   def update_using_iterable ( self, package_info_iter, reset=True ):
      if reset:
         self._package_info = None
      for package_info in package_info_iter:
         self.update ( package_info )

      return self._package_info
   # --- end of update_using_iterable (...) ---

   def _create ( self ):
      """Creates metadata (MetadataRoot) using the stored PackageInfo.

      It's expected that this method is called when Ebuild creation is done.

      returns: created metadata
      """
      mref = nodes.MetadataRoot()
      data = self._package_info ['desc_data']

      max_textline_width = roverlay.config.get ( 'METADATA.linewidth', 65 )

      description = None

      if USE_FULL_DESCRIPTION and 'Title' in data and 'Description' in data:
         description = data ['Title'] + ' // ' + data ['Description']

      elif 'Description' in data:
         description = data ['Description']

      elif 'Title' in data:
         description = data ['Title']

      #if description:
      if description is not None:
         mref.add (
            nodes.DescriptionNode ( description, linewidth=max_textline_width )
         )

      # these USE flags are described in profiles/use.desc,
      #  no need to include them here
      #mref.add_useflag ( 'byte-compile', 'enable byte-compiling' )
      #
      #if package_info ['has_suggests']:
      #   mref.add_useflag ( 'R_suggests', 'install optional dependencies' )

      return mref
   # --- end of update (...) ---

   def show ( self, stream ):
      if self._package_info is not None:
         return self._create().write_file ( stream )
      else:
         return False
   # --- end of show (...) ---

   def write ( self ):
      retcode = self.METADATA_SUCCESS
      if self._package_info is not None:
         # succeed if metadata empty or written
         mref = self._create()
         if mref.empty():
            retcode |= self.METADATA_EMPTY
         else:
            with open ( self.filepath, 'w' ) as fh:
               if not mref.write_file ( fh ):
                  retcode |= self.METADATA_WRITE_ERROR
      else:
         retcode |= self.METADATA_NO_PACKAGE

      self.last_write_code = retcode
      return bool ( retcode == self.METADATA_SUCCESS )
   # --- end of write (...) ---

   def decode_write_errors ( self ):
      # usually yields only one word
      def gen_decode ( code ):
         if code < 0:
            yield "<invalid>"
         else:
            if code & self.METADATA_NO_PACKAGE:
               yield "no package"

            if code & self.METADATA_EMPTY:
               yield "empty"

            if code & self.METADATA_WRITE_ERROR:
               yield "write error"

      reasons = list ( gen_decode ( self.last_write_code ) )
      return reasons if reasons else [ '<unknown>', ]
   # --- end of decode_write_errors (...) ---
