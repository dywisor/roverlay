# R overlay -- rpackage, license map
# -*- coding: utf-8 -*-
# Copyright (C) 2013 André Erdmann <dywi@mailerd.de>
# Distributed under the terms of the GNU General Public License;
# either version 2 of the License, or (at your option) any later version.

import logging
import re

import roverlay.util.mapreader

RE_WIPE = re.compile ( r'[\s\-\(\)=]+' )
RE_WORD_WIPE = re.compile (
   '[+|]?('
      'fileli[cs]en[cs]e'
      '|[,]?version'
      '|[;]?seereadme([.]txt)?'
      '|see[.]?'
      '|http[:][/]{2}.*?htm[l]?'
   ')'
)


def reduce_key ( key ):
   return RE_WORD_WIPE.sub ( '', RE_WIPE.sub ( '', key ) )


class LicenseMapParser ( roverlay.util.mapreader.ReverseDictFileParser ):
   def make_result ( self ):
      return {
         reduce_key ( k.lower() ): v for k, v in self.iter_result_pairs()
      }
   # --- end of make_result (...) ---

# --- end of LicenseMapParser ---


class LicenseMap ( object ):
   def __init__ ( self, portdir_licenses, mapfile=None ):
      super ( LicenseMap, self ).__init__()

      self.logger = logging.getLogger ( self.__class__.__name__ )
      self.license_map_portage = { k.lower(): k for k in portdir_licenses }

      self.license_map_file = None
      if mapfile:
         self.load_file ( mapfile )
   # --- end of __init__ (...) ---

   def load_file ( self, filepath ):
      parser = LicenseMapParser()
      parser.read_file ( filepath )
      ldict  = parser.done()

      self.license_map_file = ldict
      self.lookup_file      = ldict.get
   # --- end of load_file (...) ---

   def lookup ( self, key ):
      # common case is that both license maps are present
      k = reduce_key ( key.lower().strip() )
      if not k:
         return False

      try:
         return self.license_map_portage [k]
      except KeyError:
         pass

      if self.license_map_file:
         # else no license_map_file
         try:
            return self.license_map_file [k]
         except KeyError:
            pass

      self.logger.warning (
         "Missing license map entry for {!r} ({!r})".format ( k, key )
      )
      return None
   # --- end of lookup (...) ---

# --- end of LicenseMap ---
