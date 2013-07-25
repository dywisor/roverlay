# R overlay -- util, map file reader
# -*- coding: utf-8 -*-
# Copyright (C) 2012 André Erdmann <dywi@mailerd.de>
# Distributed under the terms of the GNU General Public License;
# either version 2 of the License, or (at your option) any later version.

import logging
import re

import roverlay.util.fileio

class MapFileParser ( object ):
   """Parser for reading <key,value^n> maps from files or text input."""

   # shared attr
   logger                = logging.getLogger ( 'MapFileParser' )
   log_unparseable       = logger.warning
   multiline_start_char  = '{'
   multiline_stop_char   = '}'
   comment_char          = '#'
   single_line_separator = re.compile ( '\s+[:][:]\s+' )

   def __init__ ( self, value_separator=None ):
      super ( MapFileParser, self ).__init__()

      if value_separator is not None:
         self.single_line_separator = re.compile ( value_separator )
         # else use shared

      self._next  = None
      # items = list ( tuple ( <key>, list ( <value(s)> ) ) )
      self._items = list()
   # --- end of __init__ (...) ---

   def zap ( self ):
      if self._next is not None:
         self.logger.warning (
            "Multi line entry does not end at EOF - ignored"
         )

      self.stop_reading = False
      self._next        = None
      self._items       = list()
   # --- end of zap (...) ---

   def has_context ( self ):
      return ( self._next is not None )
   # --- end of has_context (...) ---

   def make_result ( self ):
      return self._items
   # --- end of make_result (...) ---

   def done ( self, *args, **kwargs ):
      ret = self.make_result ( *args, **kwargs )
      self.zap()
      return ret
   # --- end of done (...) ---

   def preparse_line ( self, line ):
      return line.strip()
   # --- end of preparse_line (...) ---

   def handle_multiline_begin ( self, line ):
      self._next = ( line, list() )
      return True
   # --- end of handle_multiline_begin (...) ---

   def handle_multiline_end ( self, line ):
      self._items.append ( self._next )
      self._next = None
      return True
   # --- end of handle_multiline_end (...) ---

   def handle_multiline_append ( self, line ):
      self._next[1].append ( line )
      return True
   # --- end of handle_multiline_append (...) ---

   def handle_comment_line ( self, line ):
      return True
   # --- end of handle_comment_line (...) ---

   def handle_option_line ( self, line ):
      return False
   # --- end of handle_option_line (...) ---

   def handle_entry_line ( self, key=None, value=None ):
      if key and value:
         self._items.append ( ( key, [ value ] ) )
         return True
      else:
         return False
   # --- end of handle_entry_line (...) ---

   def add ( self, line ):
      l = self.preparse_line ( line )

      if not l:
         return True
      elif self._next is not None:
         if l[0] == self.multiline_stop_char:
            # end of a multiline entry
            #  add it to self._items and set next to None
            return self.handle_multiline_end ( l[1:].lstrip() )
         else:
            return self.handle_multiline_append ( l )

      elif l[0] == self.comment_char:
         #  it's intentional that multi line rules cannot contain comments
         return self.handle_comment_line ( l[1:].lstrip() )

      elif self.handle_option_line ( l ):
         return True

      elif len ( l ) > 1 and l[-1] == self.multiline_start_char:
         return self.handle_multiline_begin ( l[:-1].rstrip() )

      else:
         return self.handle_entry_line (
            *self.single_line_separator.split ( l, 1 )
         )
   # --- end of add (...) ---

   def read_lines_done ( self ):
      pass
   # --- end of read_lines_done (...) ---

   def read_lines_begin ( self ):
      pass
   # --- end of read_lines_begin (...) ---

   def read_lines ( self, lines, src=None ):
      self.read_lines_begin()
      self.stop_reading = False
      ret = True
      for lino, line in enumerate ( lines ):
         if not self.add ( line ):
            ret = False
            self.log_unparseable (
               "{f}: cannot parse line {n:d}: {txt!r}".format (
                  f=( src or "<input>" ), n=lino+1, txt=line
               )
            )

         if self.stop_reading:
            break

      self.read_lines_done()
      return ret
   # --- end of read_lines (...) ---

   def read_file ( self, filepath, handle_compressed=True ):
      try:
         if handle_compressed:
            ret = self.read_lines (
               roverlay.util.fileio.read_text_file ( filepath ), filepath
            )
         else:
            with open ( filepath, 'rt' ) as FH:
               ret = self.read_lines ( FH.readlines(), filepath )
      except IOError:
         self.logger.error (
            "Could not read file {!r}.".format ( filepath )
         )
         raise

      return ret
   # --- end of read_file (...) ---

# --- end of MapFileParser ---


class DictFileParser ( MapFileParser ):
   """MapFileParser that creates a dict as result."""

   def make_result ( self, unpack_values=True, strict_unpack=False ):
      def unpacked ( value ):
         if value:
            return value[0] if len ( value ) == 1 else value
         else:
            return None
      # --- end of unpacked (...) ---

      can_unpack = True

      if strict_unpack and can_unpack:
         for k, v in self._items:
            if len ( v ) > 1:
               assert not isinstance ( v, str )
               can_unpack = False
               break


      if can_unpack:
         return { k: unpacked ( v ) for k, v in self._items }
      else:
         return { k: v for k, v in self._items }
   # --- end of make_result (...) ---

# --- end of DictFileParser ---


class ReverseDictFileParser ( MapFileParser ):
   """Like DictFileParser,
   but creates a "<value,key> for value in value^n" dict.
   """

   # this is the common case for map files used in roverlay,
   #  multiple values should be mapped to a single key
   #  (e.g. dependency rules, but the depres parser doesn't use this class)
   #

   def iter_result_pairs ( self ):
      for value, keys in self._items:
         for key in keys:
            if key:
               yield ( key, value )
   # --- end of iter_pairs (...) ---

   def make_result ( self ):
      return { k: v for k, v in self.iter_result_pairs() }
   # --- end of make_result (...) ---

# --- end of ReverseDictFileParser ---
