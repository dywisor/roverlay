# R overlay -- admin webgui, constants
# -*- coding: utf-8 -*-
# Copyright (C) 2014 André Erdmann <dywi@mailerd.de>
# Distributed under the terms of the GNU General Public License;
# either version 2 of the License, or (at your option) any later version.

import collections
import itertools

class NavbarItem ( object ):

   _ID_GEN = itertools.count(1)

   def __init__ ( self, name, url, key=None ):
      super ( NavbarItem, self ).__init__()
      self.key  = ( next ( self.__class__._ID_GEN ) ) if key is None else key
      self.name = name
      self.url  = url
   # --- end of __init__ (...) ---

# --- end of NavbarItem ---

def _navbar_item ( url, name ):
   return ( url.strip("/"), NavbarItem ( name, url ) )
# --- end of _navbar_item (...) ---

def _navbar_tab_items ( navbar_str_key, *pairs ):
   navbar_item = NAVBAR_ITEMS [navbar_str_key.strip("/")]
   key         = navbar_item.key
   base_url    = navbar_item.url.rstrip("/") + "/"

   return (
      key,
      [
         NavbarItem ( args[0], base_url + args[1], key=k )
         for k, args in enumerate(pairs)
      ]
   )
# --- end of _navbar_tab_items (...) ---


TEMPLATE_SUB_PATH = r'rvadmin/'

CONFIG_SUBURL   = r'config/'
PKGRULES_SUBURL = r'pkgrules/'
DEPRULES_SUBURL = r'deprules/'


NAVBAR_ITEMS = collections.OrderedDict ((
   _navbar_item ( CONFIG_SUBURL,   "Config" ),
   _navbar_item ( DEPRULES_SUBURL, "Dependency Rules" ),
   _navbar_item ( PKGRULES_SUBURL, "Package Rules" ),
))


NAVBAR_TAB_ITEMS = dict ((
   _navbar_tab_items ( DEPRULES_SUBURL,
      ( "str view", "depstr/" ), ( "rule view", "deprule/" )
   ),
))

NAVBAR_DROPDOWN_ITEMS = collections.OrderedDict ((
))
