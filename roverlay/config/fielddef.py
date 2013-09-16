# R overlay -- config package, fielddef
# -*- coding: utf-8 -*-
# Copyright (C) 2012 André Erdmann <dywi@mailerd.de>
# Distributed under the terms of the GNU General Public License;
# either version 2 of the License, or (at your option) any later version.

"""Loads and creates field definition data from a file.

This module defines the following classes:
* DescriptionFieldDefinition
"""

__all__ = [ 'DescriptionFieldDefinition', ]

import os
import errno
import itertools

try:
   import configparser
except ImportError as running_python2:
   # configparser is named ConfigParser in python2
   import ConfigParser as configparser
# -- end try


import roverlay.rpackage.descriptionfields
import roverlay.rpackage.licensemap
import roverlay.util.fileio



class DescriptionFieldDefinition ( object ):
   """Loads field definition data and the license map."""


   def __init__ ( self, logger, config ):
      """Initializes a DescriptionFieldDefinition object.

      arguments:
      * logger -- logger to use
      * config --
      """
      super ( DescriptionFieldDefinition, self ).__init__()
      self.logger  = logger
      self.config  = config
      self._parser = configparser.SafeConfigParser ( allow_no_value=True )
   # --- end of __init__ (...) ---

   def load_file ( self, def_file, lenient=False ):
      """Loads a field definition file.
      Please see the example file for format details.

      arguments:
      * def_file -- file (str) to read,
                     this can be a list of str if lenient is True
      * lenient  -- if True: do not fail if a file cannot be read;
                     defaults to False
      """

      try:
         self.logger.debug (
            "Reading description field definition file {}.".format ( def_file )
         )
         if lenient:
            self._parser.read ( def_file )
         else:
            with open ( def_file, 'r' ) as FH:
               self._parser.readfp ( FH )
      except IOError as err:
         self.logger.exception ( err )
         raise
      except configparser.MissingSectionHeaderError as mshe:
         self.logger.exception ( mshe )
         raise

   # --- end of load_file (...) ---

   def _create_license_map ( self ):
      # get $PORTDIR/licenses/* or read license file ($PORTDIR is preferred)

      LICENSE_FILE = self.config.get ( 'LICENSEMAP.licenses_file' )
      if not LICENSE_FILE and self.config.get ( 'CACHEDIR.root' ):
         LICENSE_FILE = (
            self.config.get ( 'CACHEDIR.root' ) + os.sep + 'licenses'
         )

      # for writing the licenses file
      LICENSE_FILE_COMPRESSION = self.config.get (
         'LICENSEMAP.licenses_file_compression', 'bzip2'
      )

      # tri-state CREATE_LICENSE_FILE (True,False,None):
      #
      # (True)  create licenses file (fail if license file not set)
      # (None)  create licenses file if set
      # (False) do not create licenses file
      #
      # Note:
      #  license_file is written if LICENSEMAP.licenses_file and/or
      #  CACHEDIR.root is set
      #
      ## Alternatively,
      ##  self.config.get ( 'LICENSEMAP.licenses_file', False )
      ## instead of bool ( LICENSE_FILE )
      CREATE_LICENSE_FILE = self.config.get (
         'LICENSEMAP.create_licenses_file', bool ( LICENSE_FILE )
      )

      TRY_PORTDIR_LICENSES = self.config.get_or_fail (
         'LICENSEMAP.use_portdir'
      )
      PORTDIR = self.config.get ( 'portdir' )

      # -- end "constants"


      licenses_list = None

      if TRY_PORTDIR_LICENSES and PORTDIR:
         portage_license_dir = PORTDIR + os.sep + 'licenses'

         try:
            portage_licenses = os.listdir ( portage_license_dir )
         except OSError as oserr:
            if oserr.errno != errno.ENOENT:
               raise
         else:
            self.logger.debug (
               "Using {n:d} licenses from dir: {!r}".format (
                  portage_license_dir, n=len ( portage_licenses )
               )
            )
            licenses_list = portage_licenses
      # -- end if <try to read from portdir>

      if licenses_list is None:
         if not LICENSE_FILE:
            raise Exception (
               "config: LICENSEMAP.licenses_file is not set."
            )

         licenses_list = list (
            itertools.chain.from_iterable (
               line.strip().split ( None ) for line in
                  roverlay.util.fileio.read_text_file ( LICENSE_FILE )
            )
         )

         self.logger.debug (
            "Using {n:d} licenses from file: {!r}".format (
               LICENSE_FILE, n=len ( licenses_list )
            )
         )

      elif CREATE_LICENSE_FILE:
         roverlay.util.fileio.write_text_file (
            LICENSE_FILE, sorted ( licenses_list ), LICENSE_FILE_COMPRESSION
         )

         self.logger.debug (
            "Wrote licenses file: {!r}".format ( LICENSE_FILE )
         )
      # -- end if <read from file> / <create licenses file>

      return roverlay.rpackage.licensemap.LicenseMap (
         licenses_list, self.config.get ( 'LICENSEMAP.file', None ),
      )
   # --- end of _create_license_map (...) ---

   def get ( self ):
      """Creates and returns field definition data. Please see the example
      field definition config file for details.
      """

      def get_list ( value_str ):
         if value_str is None:
            return []
         else:
            l = value_str.split ( ', ' )
            return [ e for e in l if e.strip() ]


      fdef   = roverlay.rpackage.descriptionfields.DescriptionFields()
      parser = self._parser


      for field_name in parser.sections():
         field = (
            roverlay.rpackage.descriptionfields.DescriptionField ( field_name )
         )

         for option, value in parser.items ( field_name, 1 ):
            if option == 'alias' or option == 'alias_withcase':
               for alias in get_list ( value ):
                  field.add_simple_alias ( alias, True )

            elif option == 'alias_nocase':
               for alias in get_list ( value ):
                  field.add_simple_alias ( alias, False )

            elif option == 'default_value':
               field.set_default_value ( value )

            elif option == 'allowed_value':
               field.add_allowed_value ( value )

            elif option == 'allowed_values':
               for item in get_list ( value ):
                  field.add_allowed_value ( item )

            elif option == 'flags':
               for flag in get_list ( value ):
                  field.add_flag ( flag )

            else:
               # treat option as flag
               field.add_flag ( option )

         fdef.add ( field )
      # --- end for;

      fdef.update()

      if fdef.get_fields_with_flag ( 'isLicense' ):
         fdef.license_map = self._create_license_map()

      return fdef
   # --- end of get (...) ---
