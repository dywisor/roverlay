# R overlay -- common webgui functionality
# -*- coding: utf-8 -*-
# Copyright (C) 2014 André Erdmann <dywi@mailerd.de>
# Distributed under the terms of the GNU General Public License;
# either version 2 of the License, or (at your option) any later version.
from __future__ import unicode_literals, absolute_import, print_function

import rvcommon.util

import rvcommon.base.fields
import rvcommon.portage.fields
import rvcommon.depres.fields

from rvcommon.base.fields    import *
from rvcommon.portage.fields import *
from rvcommon.depres.fields  import *


EXPORT_FIELDS = rvcommon.util.dedup_attr_lists (
   'EXPORT_FIELDS',
   rvcommon.base.fields, rvcommon.portage.fields, rvcommon.depres.fields
)

__all__ = EXPORT_FIELDS
