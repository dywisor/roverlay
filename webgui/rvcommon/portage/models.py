# R overlay -- common webgui models
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
import rvcommon.portage.regex

# import all from base.{fields,models}, but don't export them here
from rvcommon.base.fields    import *
from rvcommon.base.models    import *
from rvcommon.portage.fields import *
from rvcommon.util           import (
   get_or_create_model, create_model, get_revmap
)


EXPORT_MODELS = [
   'Category', 'DependencyAtom', 'DependencyAtomBase',
   'FreeDependencyAtom', 'Package',
   'VersionSuffix', 'VersionSuffixItem', 'VersionSuffixRelation',
]

__all__ = EXPORT_MODELS

# Create your models here.

MAX_CATEGORY_NAME_LENGTH = 60
MAX_PACKAGE_NAME_LENGTH  = 60








class VersionSuffixItem ( UnicodeWrappedModel ):
   """
   Object representing a single (alpha|beta|pre|rc|p)<digit><digit>* sequence
   """

   VERSION_SUFFIX_ALPHA             = 1
   VERSION_SUFFIX_BETA              = 2
   VERSION_SUFFIX_PRE_RELEASE       = 3
   VERSION_SUFFIX_RELEASE_CANDIDATE = 4
   VERSION_SUFFIX_PATCH             = 5

   VERSION_SUFFIX_MAP = dict ((
      ( VERSION_SUFFIX_ALPHA,             'alpha' ),
      ( VERSION_SUFFIX_BETA,              'beta'  ),
      ( VERSION_SUFFIX_PRE_RELEASE,       'pre'   ),
      ( VERSION_SUFFIX_RELEASE_CANDIDATE, 'rc'    ),
      ( VERSION_SUFFIX_PATCH,             'p'     ),
   ))

   VERSION_SUFFIX_REVMAP = get_revmap ( VERSION_SUFFIX_MAP.items() )

   # attributes
   suffix_type = ChoiceField ( VERSION_SUFFIX_MAP, None )
   ## Text/CharField, IntegerField?
   value       = models.PositiveSmallIntegerField()

   class Meta:
      unique_together = [ ( 'suffix_type', 'value' ) ]

   def __str__ ( self ):
      try:
         return (
            self.__class__.VERSION_SUFFIX_MAP[self.suffix_type]
           + str ( self.value )
        )
      except KeyError:
         return super ( VersionSuffixItem, self ).__str__()

# --- end of VersionSuffixItem ---


class VersionSuffix ( UnicodeStrConstructorModel ):
   RE_VERSION_SUFFIX = rvcommon.portage.regex.DEP_ATOM_VERSION_SUFFIX

   items = models.ManyToManyField (
      VersionSuffixItem, through='VersionSuffixRelation'
   )

   class Meta:
      verbose_name_plural = "version suffixes"


   @classmethod
   def _from_str ( cls, constructor_method, s ):
      def pairwise ( iterable, buf_none ):
         buf = buf_none

         for k in iterable:
            assert k is not buf_none
            if buf is buf_none:
               buf = k
            else:
               if buf and k:
                  yield ( buf, k )
               buf = buf_none

         if buf is not buf_none:
            raise ValueError()
      # --- end of pairwise (...) ---

      if not s:
         raise ValueError(s)


      re_vsuffix = cls.RE_VERSION_SUFFIX

      pairs = []
      for substr in ( s[1:] if s[0] == '_' else s ).split("_"):
         match = re_vsuffix.match(substr)
         if match is None:
            raise ValueError ( "cannot parse {!r}: {!r}".format ( s, substr ) )

         type_str, value_str = match.groups()

         pairs.append (
            ( VersionSuffixItem.VERSION_SUFFIX_REVMAP[type_str], value_str )
         )

      if not pairs:
         raise ValueError(s)


      # always create a new instance (!)
      instance = cls.objects.create()

      for k, pair in enumerate ( pairs ):
         get_or_create_model (
            VersionSuffixRelation,
            item   = get_or_create_model (
               VersionSuffixItem, suffix_type=pair[0], value=pair[1]
            ),
            suffix = instance,
            index  = k,
         )
      # -- end for

      return instance
   # --- end of _from_str (...) ---

   def get_suffix_str ( self ):
      return '_'.join ( map ( str, self.items.all() ) )

   def __eq__ ( self, other ):
      if isinstance ( other, str ):
         return self.get_suffix_str() == other
      else:
         return super ( VersionSuffix, self ).__eq__ ( other )

   def __ne__ ( self, other ):
      if isinstance ( other, str ):
         return self.get_suffix_str() != other
      else:
         return super ( VersionSuffix, self ).__ne__ ( other )

   __str__ = get_suffix_str

# --- end of VersionSuffix ---


class VersionSuffixRelation ( models.Model ):
   item   = models.ForeignKey ( VersionSuffixItem )
   suffix = models.ForeignKey ( VersionSuffix )
   index  = models.PositiveSmallIntegerField()

   class Meta:
      unique_together = [ ( 'item', 'index' ) ]
      ordering        = [ 'index' ]

   def __str__ ( self ):
      return "<{!s},{!s}>".format ( self.item.id, self.index )




class Category ( models.Model ):
   name = models.CharField ( max_length=MAX_CATEGORY_NAME_LENGTH, unique=True )
   #overlay|tree = ..., ... -- not needed

   class Meta:
      ordering            = [ 'name' ]
      verbose_name_plural = "categories"

   def __str__ ( self ):
      return self.name
# --- end of Category ---


class Package ( models.Model ):
   category = models.ForeignKey ( Category )
   name     = models.CharField ( max_length=MAX_PACKAGE_NAME_LENGTH )

   class Meta:
      unique_together = [ ( 'category', 'name' ) ]
      ordering        = [ 'category', 'name' ]

   def get_full_name ( self ):
      return self.category.name + "/" + self.name

   full_name = property ( get_full_name )

   def __str__ ( self ):
      try:
         return self.get_full_name()
      except Category.DoesNotExist:
         return "???/" + self.name
# --- end of Package ---


class DependencyAtomBase ( UnicodeStrConstructorModel ):
   # extended atom prefix
   ATOM_PREFIX_NONE       = 0
   ATOM_PREFIX__NEEDVER   = 2**0
   ATOM_PREFIX_REV        = 2**1 | ATOM_PREFIX__NEEDVER
   ATOM_PREFIX_BLOCK      = 2**2
   ATOM_PREFIX_BLOCKBLOCK = 2**3

   ATOM_PREFIX_CHOICES    = dict ((
      ( ATOM_PREFIX_NONE,       ''   ),
      ( ATOM_PREFIX_REV,        '~'  ),
      ( ATOM_PREFIX_BLOCK,      '!'  ),
      ( ATOM_PREFIX_BLOCKBLOCK, '!!' ),
   ))

   # atom prefix operator
   ATOM_PREFIX_OP_NONE     = 0
   ATOM_PREFIX_OP_GT       = 1
   ATOM_PREFIX_OP_GE       = 2
   ATOM_PREFIX_OP_EQ       = 3
   ATOM_PREFIX_OP_LT       = 4
   ATOM_PREFIX_OP_LE       = 5

   ATOM_PREFIX_OP_CHOICES  = dict ((
      ( ATOM_PREFIX_OP_NONE, ''   ),
      ( ATOM_PREFIX_OP_GT,   '>'  ),
      ( ATOM_PREFIX_OP_GE,   '>=' ),
      ( ATOM_PREFIX_OP_EQ,   '='  ),
      ( ATOM_PREFIX_OP_LT,   '<'  ),
      ( ATOM_PREFIX_OP_LE,   '<=' ),
   ))

   # extended atom postfix
   ATOM_POSTFIX_NONE      = 0
   ATOM_POSTFIX_V_ANY     = 1

   ATOM_POSTFIX_CHOICES   = dict ((
      ( ATOM_POSTFIX_NONE,  ''  ),
      ( ATOM_POSTFIX_V_ANY, '*' ),
   ))

   # slot operator
   ATOM_SLOTOP_NONE       = 0
   ATOM_SLOTOP_NOBREAK    = 1
   ATOM_SLOTOP_REBUILD    = 2

   ATOM_SLOTOP_CHOICES = dict ((
      ( ATOM_SLOTOP_NONE,    ''  ),
      ( ATOM_SLOTOP_NOBREAK, '*' ),
      ( ATOM_SLOTOP_REBUILD, '=' ),
   ))

   # map variants of *_CHOICES
   ATOM_PREFIX_MAP    = get_revmap ( ATOM_PREFIX_CHOICES )
   ATOM_PREFIX_OP_MAP = get_revmap ( ATOM_PREFIX_OP_CHOICES )
   ATOM_POSTFIX_MAP   = get_revmap ( ATOM_POSTFIX_CHOICES )
   ATOM_SLOTOP_MAP    = get_revmap ( ATOM_SLOTOP_CHOICES )


   def get_real_atom ( self ):
      for name in [ "dependencyatom", "freedependencyatom" ]:
         try:
            return getattr ( self, name )
         except self.__class__.DoesNotExist:
            pass

      raise self.__class__.DoesNotExist ( "real_atom" )
   # --- end of get_real_atom (...) ---

   def get_dep_atom_str ( self ):
      return self.get_real_atom().get_dep_atom_str()

   @property
   def real_atom ( self ):
      return self.get_real_atom()

   dep_atom_str = property ( get_dep_atom_str )

# --- end of DependencyAtomBase ---


class FreeDependencyAtom ( DependencyAtomBase ):
   value = models.TextField()

   class Meta:
      ordering = [ 'value' ]

   @classmethod
   def _from_str ( cls, constructor_method, s ):
      return constructor_method ( value=s )

   def get_real_atom ( self ):
      return self

   def get_dep_atom_str ( self ):
      return self.value

   def __str__ ( self ):
      s = str(self.value)
      return ( s[:52] + "..." ) if len(s) > 55 else s

class DependencyAtom ( DependencyAtomBase ):
   """dependency atom that is bound to exactly one package."""
   # regex(es) for matching dependency atoms
   RE_DEP_ATOM = rvcommon.portage.regex.DEP_ATOM

   # attributes
   prefix = ChoiceField (
      DependencyAtomBase.ATOM_PREFIX_CHOICES,
      DependencyAtomBase.ATOM_PREFIX_NONE
   )
   prefix_operator = ChoiceField (
      DependencyAtomBase.ATOM_PREFIX_OP_CHOICES,
      DependencyAtomBase.ATOM_PREFIX_OP_NONE
   )
   ## category in package
   package         = models.ForeignKey ( Package )
   version         = VersionField()
   version_suffix  = NullableForeignKey ( VersionSuffix )
   revision        = models.PositiveSmallIntegerField ( blank=True, null=True )
   postfix         = ChoiceField (
      DependencyAtomBase.ATOM_POSTFIX_CHOICES,
      DependencyAtomBase.ATOM_POSTFIX_NONE
   )
   slot            = VersionField()
   subslot         = VersionField()
   slot_operator   = ChoiceField (
      DependencyAtomBase.ATOM_SLOTOP_CHOICES,
      DependencyAtomBase.ATOM_SLOTOP_NONE
   )
   useflags        = UseFlagsField()

   @property
   def category ( self ):
      return self.package.category

   @classmethod
   def _from_str ( cls, constructor_method, s ):
      from_map = lambda m, k, default: default if k is None else m[k]
      typecast = lambda t, v: None if v is None else t(v)

      obj = None

      if len ( s.split ( None, 1 ) ) != 1:
         raise ValueError(s)

      match = cls.RE_DEP_ATOM.match(s)
      if not match:
         raise ValueError ( "{!r} cannot be parsed.".format(s) )

      d = match.groupdict()

      slot          = d.get('slot')
      subslot       = d.get('subslot')
      slot_operator = from_map (
         cls.ATOM_SLOTOP_MAP, d.get('slot_operator'), cls.ATOM_SLOTOP_NONE
      )

      # FIXME: remove after fixing the regex
      if ( slot or subslot ) and slot_operator in { cls.ATOM_SLOTOP_NOBREAK, }:
##         raise ValueError (
##            "{!r} cannot be parsed: bad slot operator.".format(s)
##         )
         raise AssertionError (
            "broken regex: illegal slot operator in {!r}".format ( s )
         )
      # -- end if

      return constructor_method (
         prefix = from_map (
            cls.ATOM_PREFIX_MAP, d.get('prefix'), cls.ATOM_PREFIX_NONE
         ),

         prefix_operator = from_map (
            cls.ATOM_PREFIX_OP_MAP,
            d.get('prefix_operator'),
            cls.ATOM_PREFIX_OP_NONE
         ),

         package = get_or_create_model (
            Package,
            category = get_or_create_model ( Category, name=d['category'] ),
            name     = d ['package'],
         ),

         version = d.get('version'),

         version_suffix = typecast (
            VersionSuffix.new_from_str, d.get('version_suffix')
         ),

         revision = typecast ( int, d.get('revision') ),

         postfix = from_map (
            cls.ATOM_POSTFIX_MAP, d.get('postfix'), cls.ATOM_POSTFIX_NONE
         ),

         slot    = slot,
         subslot = subslot,

         slot_operator = from_map (
            cls.ATOM_SLOTOP_MAP, d.get('slot_operator'), cls.ATOM_SLOTOP_NONE
         ),

         useflags = d.get('useflags'),
      )
   # --- end of _from_str (...) ---

   def get_real_atom ( self ):
      return self

   def gen_dep_atom_str ( self ):
      cls = self.__class__

      if self.prefix != cls.ATOM_PREFIX_NONE:
         yield cls.ATOM_PREFIX_CHOICES [self.prefix]

      if self.prefix_operator != cls.ATOM_PREFIX_OP_NONE:
         yield cls.ATOM_PREFIX_OP_CHOICES [self.prefix_operator]

      yield self.package.get_full_name()

      if self.version:
         yield "-" + str(self.version)

         if self.version_suffix:
            yield "_" + str(self.version_suffix)

         if self.revision:
            yield "-r" + str(self.revision)

         if self.postfix != cls.ATOM_POSTFIX_NONE:
            yield cls.ATOM_POSTFIX_CHOICES [self.postfix]
      # -- end if <version>

      if self.slot:
         yield ":" + str(self.slot)

         if self.subslot:
            yield "/" + str(self.subslot)

         if self.slot_operator:
            yield self.ATOM_SLOTOP_CHOICES [self.slot_operator]
      # -- end if <slot>

      if self.useflags:
         yield "[" + str(self.useflags) + "]"
   # --- end of gen_dep_atom_str (...) ---

   def get_dep_atom_str ( self ):
      return ''.join ( self.gen_dep_atom_str() )
   # --- end of get_dep_atom_str (...) ---

   def __str__ ( self ):
      try:
         return self.get_dep_atom_str()
      except ( ValueError, TypeError, IndexError, NotImplementedError ):
         return super ( DependencyAtom, self ).__str__()

# --- end of DependencyAtom ---
