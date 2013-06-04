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

try:
   import configparser
except ImportError as running_python2:
   # configparser is named ConfigParser in python2
   import ConfigParser as configparser

from roverlay.rpackage import descriptionfields


class DescriptionFieldDefinition ( object ):
   """Loads field definition data."""


   def __init__ ( self, logger ):
      """Initializes a DescriptionFieldDefinition object.

      arguments:
      * logger -- logger to use
      """
      self.logger  = logger
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
            fh = open ( def_file, 'r' )
            self._parser.readfp ( fh )

            if fh: fh.close()
      except IOError as err:
         self.logger.exception ( err )
         raise
      except configparser.MissingSectionHeaderError as mshe:
         self.logger.exception ( mshe )
         raise

   # --- end of load_file (...) ---

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


      fdef = descriptionfields.DescriptionFields ()

      for field_name in self._parser.sections():
         field = descriptionfields.DescriptionField ( field_name )
         for option, value in self._parser.items ( field_name, 1 ):

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
      return fdef
   # --- end of get (...) ---
