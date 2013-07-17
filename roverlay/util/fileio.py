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

if sys.hexversion >= 0x3000000:
   def iter_decode ( lv ):
      for l in lv:
         yield l.decode()
else:
   def iter_decode ( lv ):
      return lv


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


def read_text_file ( filepath, preparse=None ):
   ftype         = guess_filetype ( filepath )
   compress_open = SUPPORTED_COMPRESSION.get ( ftype[1], None )

   if compress_open is not None:
      with compress_open ( filepath, mode='r' ) as CH:
         for line in iter_decode ( CH.readlines() ):
            yield line if preparse is None else preparse ( line )
   else:
      with open ( filepath, 'rt' ) as FH:
         for line in FH.readlines():
            yield line if preparse is None else preparse ( line )


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
      NL = '\n'.encode()
      with compress_open ( filepath, mode.rstrip ( 'tu' ) ) as CH:
         for line in lines:
            CH.write ( str ( line ).encode() )
            if append_newlines:
               CH.write ( NL )
         else:
            if append_newline_eof:
               CH.write ( NL )
   else:
      with open ( filepath, mode ) as FH:
         for line in lines:
            FH.write ( str ( line ) )
            if append_newlines:
               FH.write ( newline )
         else:
            if append_newline_eof:
               FH.write ( newline )

   return True
# --- end of write_text_file (...) ---
