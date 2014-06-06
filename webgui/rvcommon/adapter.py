# R overlay -- common webgui functionality
# -*- coding: utf-8 -*-
# Copyright (C) 2014 André Erdmann <dywi@mailerd.de>
# Distributed under the terms of the GNU General Public License;
# either version 2 of the License, or (at your option) any later version.
from __future__ import unicode_literals, absolute_import, print_function

import rvcommon.util

import rvcommon.base.adapter
import rvcommon.portage.adapter
import rvcommon.depres.adapter


from rvcommon.base.adapter    import *
from rvcommon.portage.adapter import *
from rvcommon.depres.adapter  import *


EXPORT_ADAPTERS = rvcommon.util.dedup_attr_lists (
   'EXPORT_ADAPTERS',
   rvcommon.base.adapter, rvcommon.portage.adapter, rvcommon.depres.adapter
)

__all__ = EXPORT_ADAPTERS
