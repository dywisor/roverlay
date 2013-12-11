# R overlay -- overlay package, package directory, "minimal" ebuild parser
# -*- coding: utf-8 -*-
# Copyright (C) 2012, 2013 André Erdmann <dywi@mailerd.de>
# Distributed under the terms of the GNU General Public License;
# either version 2 of the License, or (at your option) any later version.

from __future__ import print_function

import os
import shlex
import string

import roverlay.util.objects
import roverlay.strutil


STR_FORMATTER = string.Formatter()
VFORMAT       = STR_FORMATTER.vformat

class ParserException ( Exception ):
   pass
# --- end of ParserException ---


class SrcUriEntry ( object ):

   def __init__ ( self, src_uri, output_file=None ):
      super ( SrcUriEntry, self ).__init__()
      self.uri = src_uri
      if output_file:
         self.have_local = True
         self.local_file = output_file
      else:
         self.have_local = False
         self.local_file = src_uri.rpartition ( '/' ) [-1]
   # --- end of __init__ (...) ---

   def __str__ ( self ):
      if self.have_local:
         return "{URI} -> {f}".format ( URI=self.uri, f=self.local_file )
      else:
         return self.uri
   # --- end of __str__ (...) ---

# --- end of SrcUriEntry ---


class EbuildParser ( object ):

   @classmethod
   def from_file ( cls, filepath, vartable=None, unquote_value=None ):
      instance = cls ( filepath, vartable=vartable )

      if unquote_value is not None:
         instance.unquote_value = bool ( unquote_value )

      instance.read()
      return instance
   # --- end of from_file (...) ---

   def __init__ ( self, filepath, vartable=None ):
      super ( EbuildParser, self ).__init__()
      self.filepath = filepath
      self.vartable = vartable
      self.unquote_value = True
   # --- end of __init__ (...) ---

   def _read_tokens ( self, breakparse=None ):
      with open ( self.filepath, 'rt' ) as FH:
         reader                  = shlex.shlex ( FH )
         reader.whitespace_split = False
         reader.wordchars        += ' ,./$()[]:+-@*~<>'

         token = reader.get_token()
         if breakparse is None:
            while token:
               yield token
               token = reader.get_token()
         else:
            while token and not breakparse ( token ):
               yield token
               token = reader.get_token()
   # --- end of _read_tokens (...) ---

   def _read_variables ( self ):
      # assumption: no (important) variables after the first function


      # read all tokens and store them in a list
      #  this allows to look back/ahead
      tokens = list ( self._read_tokens (
         breakparse=( lambda s: ( len(s) > 2 and s[-2:] == '()' ) )
      ) )


      varname = None
      data    = dict()

      last_index    = len ( tokens ) - 1
      ignore_next   = False
      is_bash_array = False
      # 0 -> no value read, 1-> have value(s), 2 -> reject token
      value_mode    = 0

      for index, token in enumerate ( tokens ):
         if ignore_next:
            ignore_next = False
            pass

         elif index < last_index and tokens [index+1] == '=':
            # lookahead result: token is a varname
            ignore_next   = True
            is_bash_array = False
            value_mode    = 0
            varname       = token
            data [token]  = None

         elif value_mode == 0:
            if value_mode == 0 and token == '()':
               is_bash_array  = True
               value_mode     = 2
               data [varname] = []

            elif value_mode == 0 and token == '(':
               is_bash_array  = True
               value_mode     = 1
               data [varname] = []

            else:
               data [varname] = token
               value_mode     = 1

         elif value_mode > 1:
            pass

         elif is_bash_array:
            # impiles value_mode != 0

            if token == ')':
               value_mode = 2
            else:
               data [varname].append ( token )

#         else:
#            pass


      if self.unquote_value:
         return {
            varname: roverlay.strutil.str_foreach (
               roverlay.strutil.unquote, value
            ) for varname, value in data.items()
         }
      else:
         return data
   # --- end of _read_variables (...) ---

   def _get_src_uri_entries ( self, value ):
      assert isinstance ( value, str )

      src_uri         = None
      want_local_file = False

      for s in value.split():
         if not s or s[-1] == '?' or s in { '(', ')' }:
            pass

         elif want_local_file:
            yield SrcUriEntry ( src_uri, s )
            want_local_file = False
            src_uri = None

         elif s == '->':
            if src_uri is None:
               raise Exception (
                  "SRC_URI: arrow operator -> without preceding URI"
               )
            else:
               want_local_file = True

         else:
            if src_uri is not None:
               yield SrcUriEntry ( src_uri )
            src_uri = s

      # -- end for

      if want_local_file:
         raise Exception ( "SRC_URI: arrow operator -> without local file" )

      elif src_uri is not None:
         yield SrcUriEntry ( src_uri )
   # --- end of _get_src_uri_entries (...) ---

   @roverlay.util.objects.abstractmethod
   def read ( self ):
      pass
   # --- end of read (...) ---

# --- end of EbuildParser ---


class SrcUriParser ( EbuildParser ):

   def __init__ ( self, filepath, vartable=None ):
      super ( SrcUriParser, self ).__init__ ( filepath, vartable=vartable )
      self.src_uri = None
   # --- end of __init__ (...) ---

   def iter_entries ( self ):
      if self.src_uri:
         for entry in self.src_uri:
            yield entry
   # --- end of _iterate (...) ---

   def iter_entries_and_local_files (
      self, ignore_unparseable=False, yield_unparseable=False
   ):
      def convert_chars_with_vars ( text ):
         mode = 0
         for index, char in enumerate ( text ):

            if mode == 0:
               if char == '$':
                  mode = 1
               else:
                  yield char

            elif mode == 1:
               if char == '{':
                  yield char
                  mode = 2
               else:
                  raise ParserException (
                     'cannot convert variable starting at '
                     'position {:d} in {}'.format ( index, text )
                  )

            elif mode == 2 and char in { '/', }:
               raise ParserException (
                  'unsupported char {} inside variable at '
                  'position {:d} in {}'.format ( char, index, text )
               )

            else:
               yield char
      # --- end of convert_chars_with_vars (...) ---

      if self.vartable is None:
         varstr = lambda s:  ''.join ( convert_chars_with_vars ( s ) )
      else:
         varstr = lambda s: VFORMAT (
            ''.join ( convert_chars_with_vars ( s ) ), (), self.vartable
         )

      if self.src_uri:
         for entry in self.src_uri:
            local_file = entry.local_file
            if '$' in local_file:
               if ignore_unparseable:
                  try:
                     yield ( entry, varstr ( local_file ) )
                  except ParserException:
                     if yield_unparseable in { None, True }:
                        yield ( entry, None )
                     elif yield_unparseable:
                        yield ( entry, local_file )

                  except ( KeyError, IndexError ) as err:
                     # FIXME debug print
                     print (
                        "FIXME: {} {} occured while parsing {!r}".format (
                           err.__class__.__name__, str(err), local_file
                        )
                     )
                     if yield_unparseable in { None, True }:
                        yield ( entry, None )
                     elif yield_unparseable:
                        yield ( entry, local_file )
               else:
                  yield ( entry, varstr ( local_file ) )

            else:
               yield ( entry, local_file )
   # --- end of iter_entries_and_local_files (...) ---

   def iter_local_files (
      self, ignore_unparseable=False, yield_unparseable=False
   ):
      for entry, local_file in self.iter_entries_and_local_files (
         ignore_unparseable=ignore_unparseable,
         yield_unparseable=yield_unparseable
      ):
         yield local_file
   # --- end of iter_local_files (...) ---

   def __iter__ ( self ):
      return self.iter_entries()
   # --- end of __iter__ (...) ---

   def read ( self ):
      data = self._read_variables()

      if 'SRC_URI' in data:
         self.src_uri = list (
            self._get_src_uri_entries ( data ['SRC_URI'] )
         )
   # --- end of read (...) ---

# --- end of SrcUriParser ---


if __name__ == '__main__':
   import os
   import sys

   get_basename = os.path.basename

   files = sys.argv[1:]
   if files:
      name_width = min ( 50, max ( len(get_basename(s)) for s in files ) )
      for f in files:
         if f == '-':
            raise Exception ( "input from stdin is not supported." )
         else:
            parser = SrcUriParser.from_file ( f )
            for entry, local_file in parser.iter_entries_and_local_files():
               print (
                  "{name:<{l}} : {uri!s} => {locfile!s}".format (
                     name=get_basename(f), uri=entry, locfile=local_file,
                     l=name_width
                  )
               )
   else:
      sys.stderr.write (
         "Usage: {prog} <ebuild file>...\n".format (
            prog=os.path.basename ( sys.argv[0] )
         )
      )
# --- end of __main__ (...) ---
