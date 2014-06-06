# R overlay -- webgui, admin
# -*- coding: utf-8 -*-
# Copyright (C) 2014 André Erdmann <dywi@mailerd.de>
# Distributed under the terms of the GNU General Public License;
# either version 2 of the License, or (at your option) any later version.

from django.contrib import admin

import rvcommon.models
import rvadmin.models

from rvcommon.util import register_models

# Register your models here.

register_models ( rvadmin.models )
