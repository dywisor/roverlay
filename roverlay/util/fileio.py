# R overlay -- util, file read operations
# -*- coding: utf-8 -*-
# Copyright (C) 2012 André Erdmann <dywi@mailerd.de>
# Distributed under the terms of the GNU General Public License;
# either version 2 of the License, or (at your option) any later version.

import gzip
import bz2
import mimetypes
import sys

import roverlay.util.common
import roverlay.strutil
from roverlay.strutil import bytes_try_decode


_MIME = mimetypes.MimeTypes()

guess_filetype = _MIME.guess_type

COMP_GZIP  = 1
COMP_BZIP2 = 2

SUPPORTED_COMPRESSION = {
   'gzip'     : gzip.GzipFile,
   'gz'       : gzip.GzipFile,
   COMP_GZIP  : gzip.GzipFile,
   'bzip2'    : bz2.BZ2File,
   'bz2'      : bz2.BZ2File,
   COMP_BZIP2 : bz2.BZ2File,
}

def strip_newline ( s ):
   return s.rstrip ( '\n' )
# --- end of strip_newline (...) ---

def read_compressed_file_handle ( CH, preparse=None ):
   if preparse is None:
      for line in CH.readlines():
         yield bytes_try_decode ( line )
   elif preparse is True:
      for line in CH.readlines():
         yield strip_newline ( bytes_try_decode ( line ))
   else:
      for line in CH.readlines():
         yield preparse ( bytes_try_decode ( line ) )
# --- end of read_compressed_file_handle (...) ---

def read_text_file ( filepath, preparse=None, try_harder=True ):
   """Generator that reads a compressed/uncompressed file and yields text
   lines. Optionally preparses the rext lines.

   arguments:
   * filepath   -- file to read
   * preparse   -- function for (pre-)parsing lines
   * try_harder -- try known compression formats if file extension cannot
                   be detected (defaults to True)
   """


   ftype         = guess_filetype ( filepath )
   compress_open = SUPPORTED_COMPRESSION.get ( ftype[1], None )

   if compress_open is not None:
      with compress_open ( filepath, mode='r' ) as CH:
         for line in read_compressed_file_handle ( CH, preparse ):
            yield line

   elif try_harder:
      # guess_filetype detects file extensions only
      #
      #  try known compression formats
      #
      for comp in ( COMP_BZIP2, COMP_GZIP ):
         CH = None
         try:
            CH = SUPPORTED_COMPRESSION [comp] ( filepath, mode='r' )
            for line in read_compressed_file_handle ( CH, preparse ):
               yield line
            CH.close()
         except IOError as ioerr:
            if CH:
               CH.close()
            if ioerr.errno is not None:
               raise
         else:
            break
      else:
         with open ( filepath, 'rt' ) as FH:
            if preparse is None:
               for line in FH.readlines():
                  yield line
            elif preparse is True:
               for line in FH.readlines():
                  yield strip_newline ( line )
            else:
               for line in FH.readlines():
                  yield preparse ( line )
      # -- end for <comp>
   else:
      with open ( filepath, 'rt' ) as FH:
         if preparse is None:
            for line in FH.readlines():
               yield line
         elif preparse is True:
            for line in FH.readlines():
               yield strip_newline ( line )
         else:
            for line in FH.readlines():
               yield preparse ( line )
   # -- end if <compress_open?, try_harder?>

# --- end of read_text_file (...) ---

def write_text_file (
   filepath, lines, compression=None, mode='wt',
   append_newlines=True, append_newline_eof=False, create_dir=True,
   newline='\n'
):
   compress_open = (
      SUPPORTED_COMPRESSION [compression] if compression else None
   )

   if create_dir:
      roverlay.util.common.dodir_for_file ( filepath )

   if compress_open:
      NL = newline.encode()
      with compress_open ( filepath, mode.rstrip ( 'tu' ) ) as CH:
         for line in lines:
            CH.write ( str ( line ).encode() )
            if append_newlines:
               CH.write ( NL )

         if append_newline_eof:
            CH.write ( NL )
   else:
      with open ( filepath, mode ) as FH:
         for line in lines:
            FH.write ( str ( line ) )
            if append_newlines:
               FH.write ( newline )
         if append_newline_eof:
            FH.write ( newline )

   return True
# --- end of write_text_file (...) ---
