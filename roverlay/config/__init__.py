# R overlay -- config package (__init__)
# -*- coding: utf-8 -*-
# Copyright (C) 2012 André Erdmann <dywi@mailerd.de>
# Distributed under the terms of the GNU General Public License;
# either version 2 of the License, or (at your option) any later version.

"""config package"""

from roverlay.config.static import *

__all__ = [ 'access', 'get_loader', 'get', 'get_or_fail', 'ConfigError', ]

class ConfigError ( ValueError ):
   pass
