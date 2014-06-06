# R overlay -- common webgui functionality
# -*- coding: utf-8 -*-
# Copyright (C) 2014 André Erdmann <dywi@mailerd.de>
# Distributed under the terms of the GNU General Public License;
# either version 2 of the License, or (at your option) any later version.
from __future__ import unicode_literals, absolute_import, print_function

from django.db        import models
from django.utils.six import with_metaclass


import rvcommon.util
import rvcommon.base.models
import rvcommon.base.fields
import rvcommon.portage.fields
import rvcommon.portage.models
import rvcommon.depres.fields

# import all from {base,portage}.{fields,models}, but don't export them here
from rvcommon.base.fields    import *
from rvcommon.base.models    import *
from rvcommon.portage.fields import *
from rvcommon.portage.models import *
from rvcommon.depres.fields  import *
from rvcommon.util           import (
   get_or_create_model, create_model, get_revmap
)


EXPORT_MODELS = [
   'DependencyRule', 'DependencyString', 'FuzzySlotOptions',
   'SimpleDependencyRule', 'SlotPartsSelection',
   'OrderedDependencyRule',  'OrderedSimpleDependencyRule',
]

__all__ = EXPORT_MODELS


_STR_CATCH_ERRORS = (
   ValueError, TypeError, IndexError, KeyError, NotImplementedError
)

# Create your models here.

class SlotPartsSelection ( UnicodeWrappedModel ):
   is_immediate = models.BooleanField()
   value        = ListField ( value_separator=".." )

   class Meta:
      unique_together     = [ ( 'is_immediate', 'value' ) ]
      verbose_name        = "slot parts selection"
      verbose_name_plural = verbose_name

   def get_immediate ( self ):
      if __debug__:
         assert self.is_immediate
         assert self.value
         assert self.value[0]
      # -- end if
      return self.value[0]
   # --- end of get_immediate (...) ---

   def get_low ( self ):
      assert not self.is_immediate
      return int ( self.value[0] )
   # --- end of get_low (...) ---

   def get_high ( self ):
      assert not self.is_immediate
      try:
         if self.value[1]:
            return int ( self.value[1] )
      except IndexError:
         pass

      return None
   # --- end of get_high (...) ---

   def __str__ ( self ):
      try:
         if self.is_immediate:
            return "i" + str(self.get_immediate())
         else:
            low  = self.get_low()
            high = self.get_high()
            if high is None or high == low:
               return str(low)
            else:
               return str(low) + ".." + str(high)

      except _STR_CATCH_ERRORS:
         pass

      return super ( SlotPartsSelection, self ).__str__()
# --- end of SlotPartsSelection ---


class FuzzySlotOptions ( UnicodeWrappedModel ):
   SLOTOP_NONE    = DependencyAtom.ATOM_SLOTOP_NONE
   SLOTOP_NOBREAK = DependencyAtom.ATOM_SLOTOP_NOBREAK
   SLOTOP_REBUILD = DependencyAtom.ATOM_SLOTOP_REBUILD
   SLOTOP_CHOICES = DependencyAtom.ATOM_SLOTOP_CHOICES
   SLOTOP_MAP     = DependencyAtom.ATOM_SLOTOP_MAP

   SLOT_FLAG_WITH_VERSION = 2**0
   SLOT_FLAG_OPEN         = 2**1

   SLOT_FLAG_CHOICES = (
      ( SLOT_FLAG_WITH_VERSION, "include version in computed dep atoms" ),
      ( SLOT_FLAG_OPEN,         "leave slot value empty" ),
   )

   accepted_values = ListField ( value_separator=",", blank=True, null=True )
   slot_parts      = NullableForeignKey (
      SlotPartsSelection, related_name="%(class)s_slot"
   )
   subslot_parts   = NullableForeignKey (
      SlotPartsSelection, related_name="%(class)s_subslot"
   )
   flags           = IntMaskField ( SLOT_FLAG_CHOICES )
   slot_operator   = ChoiceField ( SLOTOP_CHOICES, SLOTOP_NONE )

   class Meta:
      verbose_name        = "fuzzy slot options"
      verbose_name_plural = verbose_name

   def gen_str_parts ( self ):
      yield "flags={:#x}".format ( self.flags )

      if self.accepted_values:
         yield "restrict=({})".format (
            ( ",".join(self.accepted_values[:3]) + ",..." )
               if len(self.accepted_values) > 3
                  else ",".join(self.accepted_values)
         )

      if self.slot_parts:
         yield "slotparts=" + str(self.slot_parts)

      if self.subslot_parts:
         yield "subslotparts=" + str(self.subslot_parts)

      if self.slot_operator != self.SLOTOP_NONE:
         yield "slotop=" + self.SLOTOP_CHOICES[self.slot_operator]


   def __str__ ( self ):
      try:
         return ','.join ( self.gen_str_parts() )
      except _STR_CATCH_ERRORS:
         pass
      return super ( FuzzySlotOptions, self ).__str__()



class DependencyRule ( UnicodeWrappedModel ):
   ## rule "rating" flags
   # enabled/disabled is stored separately as BooleanField
   #  (=> cls.objects.filter(is_enabled=True))
   # zero
   RATING_NONE       = 0
   # valid or not?
   #  using 2 'bits' for this status
   #   => if either RATING_VALID or RATING_INVALID: (in)valid rule
   #   => if both set: unknown
   #   => else: undefined
   #   (RATING_VALID==RATING_INVALID <=> unknown or undefined)
   #   (There's no distinction between unknown and undefined so far,
   #    except that (<undefined> & RATING_NONE) == 0 == <undefined>)
   #
   RATING_VALID      = 2**0
   RATING_INVALID    = 2**1
   # deprecated? (i.e. should be removed in future)
   RATING_DEPRECATED = 2**3


   RATING_CHOICES = dict ((
      ( RATING_VALID,        "valid"      ),
      ( RATING_INVALID,      "invalid"    ),
      ( RATING_DEPRECATED,   "deprecated" ),
   ))

   RATING_MAP = get_revmap(RATING_CHOICES)

   # attributes
   priority   = models.SmallIntegerField ( blank=True, null=True )
   comments   = NullableManyToManyField ( RatedComment, default=None )
   is_enabled = models.BooleanField ( default=True )
   rating     = IntMaskField ( RATING_CHOICES )


   def get_real_rule ( self ):
      for name in [ "simpledependencyrule", ]:
         try:
            return getattr ( self, name )
         except self.__class__.DoesNotExist:
            pass

      raise self.__class__.DoesNotExist ( "real_rule" )
   # --- end of get_real_rule (...) ---

   @property
   def real_rule ( self ):
      return self.get_real_rule()

   def __str__ ( self ):
      try:
         real_rule = self.get_real_rule()
      except DependencyRule.DoesNotExist:
         return super ( DependencyRule, self ).__str__()
      else:
         return "{cls.__name__}: {obj!s}".format (
            cls=real_rule.__class__, obj=real_rule
         )
   # --- end of __str__ (...) ---

# --- end of DependencyRule ---


class OrderedDependencyRule ( DependencyRule ):

   class Meta:
      proxy    = True
      ordering = [ 'priority' ]


class SimpleDependencyRule ( DependencyRule ):
   MATCHTYPE_EXTERNAL = 2**0
   MATCHTYPE_INTERNAL = 2**1
   MATCHTYPE_SELFDEP  = 2**2

   # match types controlled by a dep rule pool
   MATCHTYPE__RULEPOOL      = MATCHTYPE_EXTERNAL  | MATCHTYPE_INTERNAL
   MATCHTYPE__RULEPOOL_MASK = MATCHTYPE__RULEPOOL | MATCHTYPE_SELFDEP

   MATCHTYPE_CHOICES = (
      ( MATCHTYPE_EXTERNAL, "system" ),
      ( MATCHTYPE_INTERNAL, "package" ),
      ( MATCHTYPE_SELFDEP,  "overlay-hosted" ),
   )


   RULETYPE__IGNORE       = 2**0
   RULETYPE__NORMAL       = 2**1
   RULETYPE__FUZZY        = 2**2
   RULETYPE__FUZZY_SLOT   = 2**3

   RULETYPE_NORMAL        = RULETYPE__NORMAL
   RULETYPE_NORMAL_IGNORE = RULETYPE__NORMAL | RULETYPE__IGNORE
   RULETYPE_FUZZY         = RULETYPE__FUZZY
   RULETYPE_FUZZY_IGNORE  = RULETYPE__FUZZY | RULETYPE__IGNORE
   RULETYPE_FUZZY_SLOT    = RULETYPE__FUZZY | RULETYPE__FUZZY_SLOT

   RULETYPE_CHOICES = dict ((
      ( RULETYPE_NORMAL,        "normal rule" ),
      ( RULETYPE_NORMAL_IGNORE, "ignore rule" ),
      ( RULETYPE_FUZZY,         "version-relative rule" ),
      ( RULETYPE_FUZZY_IGNORE,  "version-relative ignore rule" ),
      ( RULETYPE_FUZZY_SLOT,    "version/slot-relative rule" ),
   ))

   # attributes
   dep_atom     = NullableForeignKey ( DependencyAtomBase )
   match_type   = IntMaskField ( MATCHTYPE_CHOICES )
   rule_type    = ChoiceField ( RULETYPE_CHOICES, None )
   slot_options = NullableForeignKey ( FuzzySlotOptions )

   def get_real_rule ( self ):
      return self

   def query_dep_strings ( self ):
      return self.dependencystring_set.all()

   def get_dep_atom_str ( self ):
      if self.dep_atom is None:
         return None
      else:
         return self.dep_atom.get_dep_atom_str()

   dep_atom_str = property ( get_dep_atom_str )

   def __str__ ( self ):
      def gen_str():
         cls = self.__class__
         yield cls.RULETYPE_CHOICES [self.rule_type]

         yield  " <"
         if self.match_type:
            yield ",".join (
               ( desc for k, desc in cls.MATCHTYPE_CHOICES
                  if k & self.match_type
               )
            )
         else:
            yield "none"

         yield "> "
         yield repr(str(self.get_dep_atom_str()))
      # --- end of gen_str (...) ---

      try:
         return "".join ( gen_str() )
      except _STR_CATCH_ERRORS as e:
         pass

      return super ( SimpleDependencyRule, self ).__str__()
# --- end of SimpleDependencyRule ---


class OrderedSimpleDependencyRule ( SimpleDependencyRule ):

   class Meta:
      proxy    = True
      ordering = [ 'priority', 'match_type' ]


class DependencyString ( UnicodeWrappedModel ):
   rules = NullableManyToManyField ( DependencyRule )
   value = models.TextField()

   #ISSUES/COMMENTS = <>.ManyToManyField ( ISSUE_CLS, null=True, blank=True )
   #IS_ENABLED      = <>.BooleanField(...)

   def __str__ ( self ):
      return str(self.value)
