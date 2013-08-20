# R overlay -- rpackage, description reader
# -*- coding: utf-8 -*-
# Copyright (C) 2012 André Erdmann <dywi@mailerd.de>
# Distributed under the terms of the GNU General Public License;
# either version 2 of the License, or (at your option) any later version.

"""read field definition files"""

__all__ = [ 'DescriptionReader', 'make_desc_packageinfo', ]

import string
import re
import sys
import tarfile
import os.path
import time
import logging

from roverlay          import config, util, strutil
from roverlay.rpackage import descriptionfields

LOG_IGNORED_FIELDS = True

STR_FORMATTER = string.Formatter()

def make_desc_packageinfo ( filepath ):
   """Creates a minimal dict that can be used as package info in the
   DescriptionReader (for testing/debugging).

   arguments:
   * filepath --
   """
   name, sep, ver = filepath.partition ( '_' )
   return dict (
      package_file  = filepath,
      package_name  = name,
      ebuild_verstr = ver,
      name          = name,
   )


class DescriptionReader ( object ):
   """Description Reader"""

   _NEEDS_SETUP = True

   DESCFILE_NAME       = None
   FIELD_SEPARATOR     = None
   FIELD_DEFINITION    = None
   WRITE_DESCFILES_DIR = None
   RE_LIST_SPLIT       = None
   RE_SLIST_SPLIT      = None

   @classmethod
   def _setup_cls ( cls ):
      cls.DESCFILE_NAME   = config.get_or_fail ( 'DESCRIPTION.file_name' )
      cls.FIELD_SEPARATOR = config.get ( 'DESCRIPTION.field_separator', ':' )

      cls.FIELD_DEFINITION = config.access().get_field_definition()
      if not cls.FIELD_DEFINITION:
         raise Exception (
            'Field definition is missing, '
            'cannot initialize DescriptionReader.'
         )

      cls.WRITE_DESCFILES_DIR = config.get (
         'DESCRIPTION.descfiles_dir', False
      )

      cls.RE_LIST_SPLIT = re.compile (
         config.get_or_fail ( 'DESCRIPTION.list_split_regex' )
      )
      cls.RE_SLIST_SPLIT = re.compile ( '\s+' )
   # --- end of _setup_cls (...) ---

   def __new__ ( cls, *args, **kwargs ):
      if cls._NEEDS_SETUP:
         cls._setup_cls()
         cls._NEEDS_SETUP = False

      return super ( DescriptionReader, cls ).__new__ ( cls, *args, **kwargs )
   # --- end of __new__ (...) ---

   def get_descfile_dest ( self ):
      descfiles_dir = self.WRITE_DESCFILES_DIR
      if descfiles_dir:
         return (
            descfiles_dir + os.sep + STR_FORMATTER.vformat (
               '{name}_{ebuild_verstr}.desc', (), self.fileinfo
            )
         )
      else:
         return None
   # --- end of get_descfile_dest (...) ---

   def __init__ ( self,
      package_info, logger,
      read_now=False, write_desc=True
   ):
      """Initializes a DESCRIPTION file reader."""
      self.fileinfo         = package_info
      self.logger           = logger.getChild ( 'desc_reader' )
      self.write_desc_file  = self.get_descfile_dest() if write_desc else None

      if read_now:
         self.run()
   # --- end of __init__ (...) ---

   def parse_file ( self, filepath ):
      desc_lines = self._get_desc_from_file ( filepath )
      if desc_lines is None:
         return None
      else:
         raw_data  = self._get_raw_data ( desc_lines )
         read_data = self._make_read_data ( raw_data )
         if read_data is None:
            return None
         else:
            return ( self._verify_read_data ( read_data ), read_data )
   # --- end of parse_file (...) ---

   @classmethod
   def parse_files ( cls, *filepaths ):
      instance = cls (
         None, logging.getLogger(), read_now=False, write_desc=False
      )
      for filepath in filepaths:
         yield instance.parse_file ( filepath )
   # --- end of parse_files (...) ---

   def get_desc ( self, run_if_unset=True ):
      if not hasattr ( self, 'desc_data' ):
         if run_if_unset:
            self.run()
         else:
            raise Exception ( "no desc data" )

      return self.desc_data
   # --- end of get_desc (...) ---

   def _make_read_data ( self, raw ):
      """Create read data (value or list of values per field) for the given
      raw data (list of text lines per field).

      arguments:
      * raw --

      returns: read data
      """
      # catch None
      if raw is None: return None

      # this dict will be returned as result later
      read = dict()

      flags = self.FIELD_DEFINITION.get_fields_with_flag

      # insert default values
      default_values = self.FIELD_DEFINITION.get_fields_with_default_value()

      for field_name in default_values.keys():
         if not field_name in raw:
            read [field_name] = default_values [field_name]


      # transfer fields from raw as string or list
      fields_join    = flags ( 'joinValues' )
      fields_isList  = flags ( 'isList' )
      fields_wsList  = flags ( 'isWhitespaceList' )
      fields_license = flags ( 'isLicense' )

      if fields_license:
         license_map = self.FIELD_DEFINITION.license_map

      list_split  = self.RE_LIST_SPLIT.split
      slist_split = self.RE_SLIST_SPLIT.split
      make_list   = lambda l : list ( filter ( None,  list_split ( l, 0 ) ) )
      make_slist  = lambda l : list ( filter ( None, slist_split ( l, 0 ) ) )

      for field_name, field_value in raw.items():

         # final value: $hardcoded > join (' ', value_line) > value_line
         # and for value_line: isList > wsList [... >= join ('', implicit)]

         if field_name in fields_license:
            license_str = license_map.lookup ( ' '.join ( field_value ) )
            if license_str and license_str != '!':
               read [field_name] = license_str

         elif field_name in fields_join:
            if field_name in fields_isList:
               # FIXME: "... if l" -- "make_list() := list(filter(None,...))"
               read [field_name] = ' '.join (
                  ' '.join ( make_list ( l ) ) for l in field_value if l
               )
            elif field_name in fields_wsList:
               read [field_name] = ' '.join (
                  ' '.join ( make_slist ( l ) ) for l in field_value if l
               )
            else:
               read [field_name] = ' '.join ( filter ( None, field_value ) )

         else:
            value_line = ''.join ( filter ( None, field_value ) )

            if field_name in fields_isList:
               read [field_name] = make_list ( value_line )

            elif field_name in fields_wsList:
               read [field_name] = make_slist ( value_line )

            else:
               read [field_name] = value_line


      return read
   # --- end of _make_read_data (...) ---

   def _verify_read_data ( self, read ):
      """Verifies read data.
      Checks that all mandatory fields are set and all fields have suitable
      values.

      Returns True (^= valid data) or False (^= cannot use package)
      """
      fref = self.FIELD_DEFINITION

      # ensure that all mandatory fields are set
      missing_fields = set ()

      for field in fref.get_fields_with_flag ( 'mandatory' ):

         if field in read:
            if not read [field]:
               missing_fields.add ( field )
            #else: ok
         else:
            missing_fields.add ( field )


      # check for fields that allow only certain values
      unsuitable_fields = set()

      restricted_fields = fref.get_fields_with_allowed_values()

      for field in restricted_fields:
         if field in read:
            if not fref.get ( field ).value_allowed ( read [field] ):
               unsuitable_fields.add ( field )

      # summarize results
      if missing_fields or unsuitable_fields:
         self.logger.info ( "Cannot use R package" ) # name?
         if missing_fields:
            self.logger.debug (
               "The following mandatory description fields are missing: {f}.".\
               format ( f=missing_fields )
            )
         if unsuitable_fields:
            self.logger.debug (
               "The following fields have unsuitable values: {f}.".format (
                  f=unsuitable_fields
            ) )

         return False
      else:
         return True
   # --- end of _verify_read_data (...) ---

   def _get_desc_from_file ( self, filepath, pkg_name='.' ):
      """Reads a file returns the description data.

      arguments:
      * filepath -- file to read (str; path to tarball or file)
      * pkg_name -- name of the package, in tarballs the description file
                    is located in <pkg_name>/ and thus this argument
                    is required. Defaults to '.', set to None to disable.

      All exceptions are passed to the caller (TarError, IOErr, <custom>).
      <filepath> can either be a tarball in which case the real DESCRIPTION
      file is read (<pkg_name>/DESCRIPTION) or a normal file.
      """

      self.logger.debug (
         "Starting to read file {f!r} ...".format ( f=filepath )
      )

      th = None
      fh = None

      try:
         # read describes how to import the lines from a file (e.g. rstrip())
         #  fh, th are file/tar handles
         read = None

         if tarfile.is_tarfile ( filepath ):
            # filepath is a tarball, open tar handle + file handle
            th = tarfile.open ( filepath, mode='r' )
            if pkg_name:
               fh = th.extractfile (
                  pkg_name + os.path.sep + self.DESCFILE_NAME
               )
            else:
               fh = th.extractfile ( self.DESCFILE_NAME )

         else:
            # open file handle only
            # COULDFIX: .Z compressed tar files could be opened here
            fh = open ( filepath, 'r' )

         if sys.version_info >= ( 3, ):
            # decode lines,
            #  encoding is unknown, could be ascii/iso8859*/utf8/<other>
            read_lines = [
               strutil.bytes_try_decode ( l ).rstrip() for l in fh.readlines()
            ]
         else:
            # python2 shouldn't need special decoding
            read_lines = [ l.rstrip() for l in fh.readlines() ]

      finally:
         if fh: fh.close()
         if th: th.close()
         del fh, th

      if read_lines and self.write_desc_file is not None:
         fh = None
         try:
            util.dodir ( DescriptionReader.WRITE_DESCFILES_DIR )
            fh = open ( self.write_desc_file, 'w' )
            fh.write (
               '=== This is debug output ({date}) ===\n'.format (
                  date=time.strftime ( '%F %H:%M:%S' )
            ) )
            fh.write ( '\n'.join ( read_lines ) )
            fh.write ( '\n' )
         finally:
            if fh:
               fh.close()

      return read_lines

   # --- end of _get_desc_from_file (...) ---

   def _get_raw_data ( self, desc_lines ):
      raw = dict()

      field_context = None

      comment_chars = config.get ( 'DESCRIPTION.comment_chars', '#' )

      non_ascii_warned = False

      for line in desc_lines:
         field_context_ref = None

         # using s(tripped)line whenever whitespace doesn't matter
         sline = line.lstrip()

         if not sline or line [0] in comment_chars:
            # empty line or comment
            pass

         elif line [0] != sline [0]:
            # line starts with whitespace

            if field_context:
               # context is set => append values

               raw [field_context].append ( sline )

            else:
               # no valid context => ignore line
               pass

         else:
            # line has to introduce a new field context, forget last one
            field_context = None

            line_components = sline.partition ( self.FIELD_SEPARATOR )

            if line_components [1]:
               # line contains a field separator => new context, set it
               field_context_ref = self.FIELD_DEFINITION.get (
                  line_components [0]
               )

               if field_context_ref is None:
                  # field not defined, skip
                  self.logger.info (
                     STR_FORMATTER.vformat (
                        "Skipped a description field: {0!r}.",
                        line_components, {}
                     )
                  )
               elif field_context_ref.has_flag ( 'ignore' ):
                  # field ignored
                  if LOG_IGNORED_FIELDS:
                     self.logger.debug (
                        "Ignored field {f!r}.".format (
                           f=field_context_ref.get_name()
                     ) )

               else:
                  field_context = field_context_ref.get_name()

                  if not field_context:
                     raise Exception (
                        'Field name is not valid! This should\'ve '
                        'already been catched in DescriptionField...'
                     )

                  new_value   = line_components [2].strip()
                  field_value = raw.get ( field_context, None )

                  if not new_value:
                     # add nothing but create field if it does not exist
                     if field_value is None:
                        raw [field_context] = []

                  elif field_value is None:
                     # create a new empty list for this field_context
                     # and add values to read_data
                     raw [field_context] = [ new_value ]

                  elif field_value:
                     # some packages have multiple Title fields
                     # warn about that 'cause it could lead to confusing
                     # ebuild/metadata output
                     self.logger.warning (
                        "field redefinition: {f!r}".format ( f=field_context )
                     )

                     field_value.append ( new_value )

                  else:
                     field_value.append ( new_value )

            else:
               # reaching this branch means that
               #  (a) line has no leading whitespace
               #  (b) line has no separator (:)
               # this should not occur in description files (bad syntax,
               # unknown compression (.Z))

               # remove non ascii-chars before logging
               # (could confuse the terminal)
               ascii_str = strutil.ascii_filter ( line_components [0] )
               if len ( ascii_str ) == len ( line_components [0] ):
                  self.logger.warning (
                     STR_FORMATTER.vformat (
                        "Unexpected line in description file: {0!r}.",
                        line_components, {}
                     )
                  )
               elif not non_ascii_warned:
                  # probably compressed text
                  self.logger.warning (
                     'Unexpected non-ascii line in description '
                     'file (compressed text?)!'
                  )
                  non_ascii_warned = True

      # -- end for --

      if raw:
         return raw
      elif non_ascii_warned:
         return None
      else:
         # empty desc_data!
         return raw

      # Alternatively, always return None if raw is empty
      #return raw or None
   # --- end of _get_raw_data (...) ---

   def run ( self ):
      """Reads a DESCRIPTION file and returns the read data if successful,
      else None.

      arguments:
      * file -- path to the tarball file (containing the description file)
                that should be read

      It does some pre-parsing, inter alia
      -> assigning field identifiers from the file to real field names
      -> split field values
      -> filter out unwanted/useless fields

      The return value is a description_data dict or None if the read data
      are "useless" (not suited to create an ebuild for it,
      e.g. if OS_TYPE is not unix).
      """
      read_data = None
      try:
         desc_lines = self._get_desc_from_file (
            self.fileinfo ['package_file'],
            self.fileinfo ['package_name']
         )
      except Exception as err:
         #self.logger.exception ( err )
         # error message should suffice
         self.logger.warning ( err )
      else:
         if desc_lines is not None:
            raw_data  = self._get_raw_data ( desc_lines )
            read_data = self._make_read_data ( raw_data )



      self.desc_data = None

      if read_data is None:
         self.logger.warning (
            STR_FORMATTER.vformat (
               "Failed to read file {package_file!r}.", (), self.fileinfo
            )
         )

      elif self._verify_read_data ( read_data ):
         self.logger.debug (
            STR_FORMATTER.vformat (
               "Successfully read file {package_file!r} with data = {0}.",
               ( read_data, ), self.fileinfo
            )
         )
         self.desc_data = read_data

      # else have log entries from _verify()

   # --- end of run (...) ---

# --- end of DescriptionReader ---


def read ( package_info, logger=None ):
   return DescriptionReader (
      package_info = package_info,
      logger       = logger or package_info.logger,
      read_now     = True
   ).get_desc ( run_if_unset=False )
# --- end of read (...) ---
