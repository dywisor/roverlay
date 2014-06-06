# R overlay -- common webgui functionality
# -*- coding: utf-8 -*-
# Copyright (C) 2014 André Erdmann <dywi@mailerd.de>
# Distributed under the terms of the GNU General Public License;
# either version 2 of the License, or (at your option) any later version.
from __future__ import unicode_literals, absolute_import, print_function

from django.db import models

EXPORT_FIELDS = [ 'UseFlagsField', 'VersionField' ]

__all__ = EXPORT_FIELDS


class UseFlagsField ( models.TextField ):
   # *** STUB ***
   def __init__ ( self, blank=True, null=True, **kwargs ):
      super ( UseFlagsField, self ).__init__ (
         blank=blank, null=null, **kwargs
      )


class VersionField ( models.TextField ):
   # *** STUB ***
   def __init__ ( self, blank=True, null=True, **kwargs ):
      super ( VersionField, self ).__init__ (
         blank=blank, null=null, **kwargs
      )
