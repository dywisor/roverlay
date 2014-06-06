# R overlay -- common webgui functionality
# -*- coding: utf-8 -*-
# Copyright (C) 2014 André Erdmann <dywi@mailerd.de>
# Distributed under the terms of the GNU General Public License;
# either version 2 of the License, or (at your option) any later version.
from __future__ import unicode_literals, absolute_import, print_function

from django.db import models

import rvcommon.util
import rvcommon.base.fields

from rvcommon.util        import get_revmap
from rvcommon.base.fields import *



EXPORT_MODELS = [ 'RatedComment', ]

__all__ = EXPORT_MODELS + [
   'UnicodeWrappedModel', 'UnicodeStrConstructorModel',
]


class UnicodeWrappedModel ( models.Model ):
   class Meta:
      abstract = True

   def __unicode__ ( self ):
      return self.__str__()


class UnicodeStrConstructorModel ( UnicodeWrappedModel ):
   class Meta:
      abstract = True

   def _from_str ( cls, constructor_method, s, *args, **kwargs ):
      raise NotImplementedError()

   @classmethod
   def from_str ( cls, s, *args, **kwargs ):
      return cls._from_str ( cls.objects.get_or_create, s, *args, **kwargs )[0]

   @classmethod
   def new_from_str ( cls, s, *args, **kwargs ):
      return cls._from_str ( cls.objects.create, s, *args, **kwargs )


class RatedComment ( UnicodeWrappedModel ):

   LEVEL_NONE    = 0
   LEVEL_DEBUG   = 1
   LEVEL_INFO    = 2
   LEVEL_NOTICE  = 3
   LEVEL_WARNING = 4
   LEVEL_ERR     = 5
   LEVEL_CRIT    = 6
   LEVEL_ALERT   = 7
   LEVEL_EMERG   = 8

   LEVEL_CHOICES = dict ((
      ( LEVEL_NONE,    "undefined" ),
      ( LEVEL_DEBUG,   "debug"     ),
      ( LEVEL_INFO,    "info"      ),
      ( LEVEL_NOTICE,  "notice"    ),
      ( LEVEL_WARNING, "warning"   ),
      ( LEVEL_ERR,     "error"     ),
      ( LEVEL_CRIT,    "critical"  ),
      ( LEVEL_ALERT,   "alert"     ),
      ( LEVEL_EMERG,   "emergency" ),
   ))


   LEVEL_MAP = get_revmap(LEVEL_CHOICES)


   rating = rvcommon.base.fields.ChoiceField ( LEVEL_CHOICES, LEVEL_NONE )
   value  = models.TextField()


   class Meta:
      unique_together = [ ( 'rating', 'value' ) ]


   def __str__ ( self ):
      try:
         return "[{level_str!s}] {value!s}".format (
            level_str = self.__class__.LEVEL_CHOICES [self.rating],
            value      = self.value
         )
      except KeyError:
         return super ( RatedComment, self ).__str__()
