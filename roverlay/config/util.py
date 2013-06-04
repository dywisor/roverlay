# R overlay -- config package, util
# -*- coding: utf-8 -*-
# Copyright (C) 2012 André Erdmann <dywi@mailerd.de>
# Distributed under the terms of the GNU General Public License;
# either version 2 of the License, or (at your option) any later version.

"""config utility functions

Provides the following functions:
* get_config_path -- get a config path
"""

__all__ = [ 'get_config_path', ]

def get_config_path ( key ):
   """Creates and returns a config path for key.

   arguments:
   * key --

   """
   _path = key.split ( '.' ) if isinstance ( key, str ) else key
   if isinstance ( _path, ( list, tuple ) ):
      # config paths are [ CAPSLOCK, CAPSLOCK,.... , lowercase item ]
      return [ x.lower() if x == _path [-1] else x.upper() for x in _path ]
   else:
      return _path
# --- end of get_config_path (...) ---
