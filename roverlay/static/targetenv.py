# R overlay --
# -*- coding: utf-8 -*-
# Copyright (C) 2014 André Erdmann <dywi@mailerd.de>
# Distributed under the terms of the GNU General Public License;
# either version 2 of the License, or (at your option) any later version.

import collections


# *** FIXME: doc ***
# gentoo means:
# * have PORTDIR
# * have ebuild(1) from portage
# and foreign -- "not gentoo":
# * don't use PORTDIR
# * don't use portage
# * use a hardcoded licenses file
# ...
#

DEFAULT_TARGET = "gentoo"

# dict: env_name(str) => defaults(TargetInfo)
TARGET_INFO = collections.OrderedDict()

#TargetInfo = collections.namedtuple ( 'TargetInfo', 'name has_portage portdir' )
class TargetInfo ( object ):
   __instances = dict()

   @classmethod
   def get_instance ( cls, *args ):
      obj = cls.__instances.get ( args, None )
      if obj is None:
         obj = cls ( *args )
         cls.__instances [args] = obj
      return obj

   def __init__ ( self, name, has_portage, portdir ):
      super ( TargetInfo, self ).__init__()
      self.name        = name
      self.has_portage = has_portage
      self.portdir     = portdir
# --- end of TargetInfo ---

def add_entry ( name, *args ):
   TARGET_INFO [name] = TargetInfo.get_instance ( name, *args )
# --- end of add_entry (...) ---


add_entry ( 'gentoo',  True, "/usr/portage" )
add_entry ( 'foreign', False, False )
