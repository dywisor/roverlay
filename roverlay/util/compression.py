# R overlay -- util, compression
# -*- coding: utf-8 -*-
# Copyright (C) 2012-2014 André Erdmann <dywi@mailerd.de>
# Distributed under the terms of the GNU General Public License;
# either version 2 of the License, or (at your option) any later version.

__all__ = [
   'COMP_GZIP', 'COMP_BZIP2', 'COMP_XZ',
   'get_all_compression_formats', 'get_supported_compression_formats',
   'check_compression_supported', 'get_compress_open',
]

import gzip
import bz2

try:
   import lzma
except ImportError:
   # python < 3.3 without backported lzma
   _HAVE_LZMA_MODULE = False
   # COULDFIX: compat hack, always catch IOError before LZMAError!
   LZMAError = IOError
else:
   _HAVE_LZMA_MODULE = True
   LZMAError = lzma.LZMAError


COMP_GZIP  = 1
COMP_BZIP2 = 2
COMP_XZ    = 3

SUPPORTED_COMPRESSION = {
   'gzip'     : gzip.GzipFile,
   'gz'       : gzip.GzipFile,
   COMP_GZIP  : gzip.GzipFile,
   'bzip2'    : bz2.BZ2File,
   'bz2'      : bz2.BZ2File,
   COMP_BZIP2 : bz2.BZ2File,
}

if _HAVE_LZMA_MODULE:
   SUPPORTED_COMPRESSION ['xz']    = lzma.LZMAFile
   SUPPORTED_COMPRESSION [COMP_XZ] = lzma.LZMAFile
# -- end if _HAVE_LZMA_MODULE

def get_all_compression_formats():
   return [ 'gzip', 'gz', 'bzip2', 'bz2', 'xz' ]
# --- end of get_all_compression_formats (...) ---

def get_supported_compression_formats():
   return [ k for k in SUPPORTED_COMPRESSION if isinstance ( k, str ) ]
# --- end of get_supported_compression_formats (...) ---

def check_compression_supported ( compression ):
   return compression in SUPPORTED_COMPRESSION
# --- end of check_compression_supported (...) ---

def get_compress_open ( compression, *args ):
   if args:
      return SUPPORTED_COMPRESSION.get ( compression, *args )
   else:
      return SUPPORTED_COMPRESSION [compression]
# --- end of get_compress_open (...) ---
