# R overlay -- common webgui models
# -*- coding: utf-8 -*-
# Copyright (C) 2014 André Erdmann <dywi@mailerd.de>
# Distributed under the terms of the GNU General Public License;
# either version 2 of the License, or (at your option) any later version.
from __future__ import unicode_literals, absolute_import, print_function

from django.db import models

import rvcommon.util
import rvcommon.fields
import rvcommon.base.models
import rvcommon.portage.models
import rvcommon.depres.models

from rvcommon.util import create_model, get_or_create_model, register_models
from rvcommon.fields         import *
from rvcommon.base.models    import *
from rvcommon.portage.models import *
from rvcommon.depres.models  import *

EXPORT_FIELDS = rvcommon.fields.EXPORT_FIELDS
EXPORT_MODELS = rvcommon.util.dedup_attr_lists (
   'EXPORT_MODELS',
   rvcommon.base.models, rvcommon.portage.models, rvcommon.depres.models,
)


__all__ = EXPORT_FIELDS + EXPORT_MODELS + [
   'create_model', 'get_or_create_model', 'register_models',
]
