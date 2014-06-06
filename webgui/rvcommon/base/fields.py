# R overlay -- common webgui functionality
# -*- coding: utf-8 -*-
# Copyright (C) 2014 André Erdmann <dywi@mailerd.de>
# Distributed under the terms of the GNU General Public License;
# either version 2 of the License, or (at your option) any later version.
from __future__ import unicode_literals, absolute_import, print_function

import gettext
_ = gettext.gettext

from django.db import models
from django.utils.six import with_metaclass
from django.core.exceptions import ValidationError

from rvcommon.util import undictify, bitsum_unique

EXPORT_FIELDS = [
   'NullableForeignKey', 'NullableOneToOneField', 'NullableManyToManyField',
   'IntMaskField', 'ChoiceField', 'ListField',
]

__all__ = EXPORT_FIELDS + [ 'create_field_wrapper', 'create_nullable', ]


def create_field_wrapper ( field_constructor, **default_kwargs ):
   def wrapped ( *args, **kwargs ):
      for k, v in default_kwargs.items():
         kwargs.setdefault ( k, v )
      return field_constructor ( *args, **kwargs )
   return wrapped

def create_nullable ( field_constructor, **default_kwargs ):
   return create_field_wrapper (
      field_constructor, blank=True, null=True, **default_kwargs
   )


NullableOneToOneField   = create_nullable ( models.OneToOneField )
NullableManyToManyField = create_nullable ( models.ManyToManyField )
NullableForeignKey      = create_nullable (
   models.ForeignKey, on_delete=models.SET_NULL
)

class IntMaskField (
   with_metaclass ( models.SubfieldBase, models.PositiveSmallIntegerField )
):

   def __init__ ( self, atoms, *args, **kwargs ):
      self.atoms         = undictify ( atoms )
      self.atom_restrict = undictify ( kwargs.pop ( 'atom_restrict', None ) )
      self.mask          = bitsum_unique ( a[0] for a in self.atoms )

      blocked_atoms = {}
      # atom => blocked_by'mask
      for blocker, atoms in self.atom_restrict:
         for atom in filter(None,atoms):
            blocked_atoms.setdefault ( atom, 0 )
            blocked_atoms [atom] |= blocker
         # -- end for
      # -- end for

      self.blocked_atoms = blocked_atoms

      super ( IntMaskField, self ).__init__ ( *args, **kwargs )
   # --- end of __init__ (...) ---

   def deconstruct ( self ):
      name, path, args, kwargs = super ( IntMaskField, self ).deconstruct()
      kwargs ['atoms'] = self.atoms
      if self.atom_restrict:
         kwargs ['atom_restrict'] = self.atom_restrict
      return name, path, args, kwargs
   # --- end of deconstruct (...) ---

   def filter_blockers ( self, value ):
      return (
         a for a in self.blocked_atoms.items()
            if ( value & a[0] and value & a[1] )
      )
   # --- end of filter_blockers (...) ---

   def validate ( self, value, *args, **kwargs ):
      super ( IntMaskField, self ).validate ( value, *args, **kwargs )
      if not value:
         pass
      elif ( value & self.mask ) != value:
         raise ValidationError (
            _("Invalid value: %(value)s"), code="invalid/mask",
            params={ "value": value }
         )
      else:
         errs = []

         blocked_err_msg = _(
            'component %(blocked)s of value %(value)s blocked by mask'
            ' %(blocker)s'
         )

         for blocked_atom, blockers in self.filter_blockers ( value ):
            errs.append (
               ValidationError (
                  blocked_err_msg,
                  code   = "invalid/blocked",
                  params = {
                     "value"   : value,
                     "blocked" : blocked_atom,
                     "blocker" : blockers,
                  }
               )
            )
         # -- end for

         if errs:
            raise ValidationError ( *errs )
      # -- end if

   # --- end of validate (...) ---

   def match_atoms ( self, value ):
      return ( atom for atom, DONT_CARE in self.atoms if ( value & atom ) )

# --- end of IntMaskField ---


class ChoiceField ( models.PositiveSmallIntegerField ):

   def __init__ ( self, choices, default, **kwargs ):
      kwargs ['choices'] = undictify ( choices )
      if __debug__:
         assert not isinstance ( kwargs['choices'], str )
         assert hasattr ( kwargs['choices'], '__iter__' )

      if default is not None:
         kwargs ['default'] = default
      super ( ChoiceField, self ).__init__ ( **kwargs )
   # --- end of __init__ (...) ---

# --- end of ChoiceField ---


class ListField (
   with_metaclass ( models.SubfieldBase, models.TextField )
):
   DEFAULT_VALUE_SEPARATOR = r'|<!|'
   DEFAULT_VALUE_TYPE      = str

   def __init__ ( self, *args, **kwargs ):
      self.value_separator = kwargs.pop (
         'value_separator', self.__class__.DEFAULT_VALUE_SEPARATOR
      )
      self.value_type = kwargs.pop (
         'value_type', self.__class__.DEFAULT_VALUE_TYPE
      )
      super ( ListField, self ).__init__ ( *args, **kwargs )
   # --- end of __init__ (...) ---

   def deconstruct ( self ):
      name, path, args, kwargs = super ( ListField, self ).deconstruct()

      def kw_add ( k, val, default ):
         if val is not default:
            # or "val != default"
            kwargs[k] = val


      cls = self.__class__
      for k in ( 'value_separator', 'value_type' ):
         kw_add (
            k, getattr(self,k), getattr(cls,'DEFAULT_'+k.upper())
         )

      return ( name, path, args, kwargs )
   # --- end of deconstruct (...) ---

   def to_python ( self, value ):
      if isinstance ( value, list ):
         return value
      elif value is None:
         return None
      elif self.value_type is str:
         return list ( value.split ( self.value_separator ) )
      else:
         return list (
            self.value_type(s) for s in value.split ( self.value_separator )
         )
   # --- end of to_python (...) ---

   def get_prep_value ( self, value ):
      if value is None:
         return None
      elif isinstance ( value, list ):
         if __debug__:
            assert all ( self.value_separator not in str(x) for x in value )

         return self.value_separator.join ( str(x) for x in value )
      else:
         raise ValueError ( "value is not a list." )
   # --- end of get_prep_value (...) ---

   def value_to_string ( self, obj ):
      return self.get_prep_value ( self._get_val_from_obj ( obj ) )
   # --- end of value_to_string (...) ---

# --- end of ListField ---
