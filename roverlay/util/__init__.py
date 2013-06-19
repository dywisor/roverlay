# R overlay -- roverlay package, util
# -*- coding: utf-8 -*-
# Copyright (C) 2013 André Erdmann <dywi@mailerd.de>
# Distributed under the terms of the GNU General Public License;
# either version 2 of the License, or (at your option) any later version.

from roverlay.util.common import *

import sys

#if sys.hexversion >= 0x4000000:
#   raise NotImplementedError()

if sys.hexversion >= 0x3000000:
   from roverlay.util.py3 import *
else:
   from roverlay.util.py2 import *

del sys
