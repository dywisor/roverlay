# R overlay -- config package, exceptions
# -*- coding: utf-8 -*-
# Copyright (C) 2014 André Erdmann <dywi@mailerd.de>
# Distributed under the terms of the GNU General Public License;
# either version 2 of the License, or (at your option) any later version.

__all__ = [
   'ConfigException', 'ConfigEntryMapException',
   'ConfigKeyError', 'ConfigOptionNotFound',
   'ConfigTreeUsageError',
]


class ConfigException ( Exception ):
   pass
# --- end of ConfigException ---

class ConfigEntryMapException ( ConfigException ):
   pass
# --- end of ConfigEntryMapException ---


class ConfigKeyError ( ConfigException ):
   # or inherit KeyError
   def __init__ ( self, config_key ):
      super ( ConfigKeyError, self ).__init__ (
         "config key {!r} not found but required.".format ( config_key )
      )
# --- end of ConfigKeyError ---

class ConfigOptionNotFound ( ConfigException ):
   pass
# --- end of ConfigOptionNotFound ---

class ConfigTreeUsageError ( ConfigException ):
   def __init__ ( self, message=None ):
      super ( ConfigTreeUsageError, self ).__init__ (
         "bad usage" if message is None else message
      )
# --- end of ConfigTreeUsageError ---
