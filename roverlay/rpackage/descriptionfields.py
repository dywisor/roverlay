# R overlay -- rpackage, description fields
# -*- coding: utf-8 -*-
# Copyright (C) 2012 André Erdmann <dywi@mailerd.de>
# Distributed under the terms of the GNU General Public License;
# either version 2 of the License, or (at your option) any later version.

"""field definition objects"""

__all__ = [ 'DescriptionField', 'DescriptionFields', ]

class DescriptionField ( object ):
   """Configuration for a field in the R package description file."""

   def __init__ ( self, name ):
      """Initializes a DescriptionField with a valid(!) name.

      arguments:
      * name -- name of the field, has to be True (neither empty nor None)

      raises: Exception if name not valid
      """

      if not name:
         raise Exception ( "description field name is empty." )

      self.name = name

      self.early_value_validation = False

      self.default_value  = None
      self.flags          = list()
      self.allowed_values = list()
      self.aliases        = dict()
   # --- end of __init__ (...) ---

   def get_name ( self ):
      """Returns the name of this DescriptionField."""
      return self.name

   # --- end of get_name (...) ---

   def add_flag ( self, flag ):
      """Adds a flag to this DescriptionField. Flags are always stored in
      their lowercase form.

      arguments:
      * flag -- name of the flag
      """
      self.flags.append ( flag.lower() )

   # --- end of add_flag (...) ---

   def add_allowed_value ( self, value ):
      """Adds an allowed value to this DescriptionField, which creates a
      value whitelist for it. You can later check if a value is allowed using
      value_allowed (<value> [, <case insensitive?>]).

      arguments:
      * value -- allowed value
      """

      self.allowed_values.append ( value )

   # --- end of add_allowed_value (...) ---

   def del_flag ( self, flag ):
      """Removes a flag from this DescriptionField. Does nothing if the flag
      does not exist.
      """
      #COULDFIX: not used
      #self.flags.discard ( flag.lower() )
      pass
   # --- end of del_flag (...) ---

   def add_alias ( self, alias, alias_type='withcase' ):
      """Adds an alias for this DescriptionField's name. This can also be used
      to combine different fields ('Description' and 'Title') or to fix
      typos ('Depend' -> 'Depends').

      arguments:
      * alias -- alias name
      * alias_type -- type of the alias
                       'nocase'   : alias is case insensitive
                       else       : alias is case sensitive

      """
      if alias_type == 'nocase':
         to_add = alias.lower()
      else:
         #assert alias_type == 'withcase'
         to_add = alias

      alias_list = self.aliases.get ( alias_type, None )

      if alias_list:
         alias_list.append ( to_add )
      else:
         self.aliases [alias_type] = [ to_add ]
   # --- end of add_alias (...) ---

   def add_simple_alias ( self, alias, withcase=True ):
      """Adds an alias to this DescriptionField. Its type is either withcase
      or nocase. See add_alias (...) for details.

      arguments:
      alias --
      withcase -- if True (the default): alias_type is withcase, else nocase

      raises: KeyError (passed from add_alias (...))
      """
      return self.add_alias ( alias, ( 'withcase' if withcase else 'nocase' ) )

   # --- end of add_simple_alias (...) ---

   def get_default_value ( self ):
      """Returns the default value for this DescriptionField if it exists,
      else None.
      """
      return self.default_value

   # --- end of get_default_value (...) ---

   def set_default_value ( self, value ):
      """Sets the default value for this this DescriptionField.

      arguments:
      * value -- new default value
      """
      self.default_value = value

   # --- end of set_default_value (...) ---

   def get_flags ( self ):
      """Returns the flags of this DescriptionField or
      an empty list (=no flags).
      """
      return self.flags

   # --- end of get_flags (...) ---

   def get_allowed_values ( self ):
      """Returns the allowed values of this DescriptionField or an empty list,
      which should be interpreted as 'no value restriction'.
      """
      return self.allowed_values

   # --- end of get_allowed_values (...) ---

   def matches ( self, field_identifier ):
      """Returns whether field_identifier equals the name of this field.

      arguments:
      * field_identifier --
      """
      if field_identifier:
         return bool ( self.name == field_identifier )
      else:
         return False
   # --- end of matches (...) ---

   def matches_alias ( self, field_identifier ):
      """Returns whether field_identifier equals any alias of this field.

      arguments:
      * field_identifier --
      """

      if not field_identifier:
         # bad identifier
         return False

      elif 'withcase' in self.aliases and (
         field_identifier in self.aliases ['withcase']
      ):
            return True

      elif 'nocase' in self.aliases:
         field_id_lower = field_identifier.lower()
         if field_id_lower in self.aliases ['nocase']:
            return True

      return False

   # --- end of matches_alias (...) ---

   def has_flag ( self, flag  ):
      """Returns whether this DescriptionField has the given flag.

      arguments:
      * flag --
      """
      return ( flag.lower() in self.flags )
   # --- end of has_flag (...) ---

   def value_allowed ( self, value, nocase=True ):
      """Returns whether value is allowed for this DescriptionField.

      arguments:
      * value -- value to check
      * nocase -- if True (the default): be case insensitive
      """

      if not self.allowed_values:
         return True
      elif nocase:
         return ( value.lower() in self.allowed_values_nocase )
      else:
         return ( value in self.allowed_values )
   # --- end of value_allowed (...) ---

   def configure ( self ):
      self.allowed_values         = frozenset ( self.allowed_values )
      self.flags                  = frozenset ( self.flags )

      if 'islicense' in self.flags:
         self.early_value_validation = True
      else:
         self.early_value_validation = False
         if self.allowed_values:
            self.allowed_values_nocase = frozenset (
               s.lower() for s in self.allowed_values
            )
   # --- end of configure (...) ---

# --- end of DescriptionField ---


class DescriptionFields ( object ):
   """DescriptionFields stores several instances of DescriptionField and
   provides 'search in all' methods such as get_fields_with_flag (<flag>).
   """

   def __init__ ( self ):
      """Initializes an DescriptionFields object."""
      self.fields = dict ()
      # result 'caches'
      ## flag -> [<fields>]
      self._fields_by_flag   = None
      ## option -> [<fields>]
      self._fields_by_option = None

   # --- end of __init__ (...) ---

   def add ( self, desc_field ):
      """Adds an DescriptionField. Returns 1 desc_field was a DescriptionField
      and has been added as obj ref, 2 if a new DescriptionField with
      name=desc_field has been created and added and 0 if this was not
      possible.

      Note:
         update() has to be called after adding one or more fields.

      arguments:
      * desc_field -- this can either be a DescriptionField or a name.
      """
      if desc_field:
         if isinstance ( desc_field, DescriptionField ):
            self.fields [desc_field.get_name()] = desc_field
            return 1
         elif isinstance ( desc_field, str ):
            self.fields [desc_field] = DescriptionField ( desc_field )
            return 2

      return 0

   # --- end of add (...) ---

   def get ( self, field_name ):
      """Returns the DescriptionField to which field_name belongs to.
      This method does, unlike others in DescriptionFields, return a
      reference to the matching DescriptionField object, not the field name!
      Returns None if field_name not found.

      arguments:
      * field_name --
      """
      field = self.fields.get ( field_name, None )
      if field is None:
         for field in self.fields.values():
            if field.matches_alias ( field_name ):
               return field
         else:
            return None
      else:
         return field

   # --- end of get (...) ---

   def find_field ( self, field_name ):
      """Determines the name of the DescriptionField to which field_name
      belongs to. Returns the name of the matching field or None.

      arguments:
      * field_name --
      """
      field = self.get ( field_name )
      if field is None:
         for field in self.fields.values():
            if field.matches_alias ( field_name ):
               return field.get_name()
      else:
         return field.get_name()

   # --- end of find_field (...) ---

   def update ( self ):
      """Scans all stored DescriptionField(s) and creates fast-accessible
      data to be used in get_fields_with_<sth> (...).

      Returns self (this object).
      """
      flagmap   = dict()
      optionmap = dict (
         defaults       = dict(),
         allowed_values = set()
      )

      for field_name, field in self.fields.items():
         field.configure()

         d = field.default_value
         if not d is None:
            optionmap ['defaults'] [field_name] = d

         if not field.early_value_validation and field.allowed_values:
            optionmap ['allowed_values'].add ( field_name )

         for flag in field.flags:
            if not flag in flagmap:
               flagmap [flag] = set()
            flagmap [flag].add ( field_name )

      self._fields_by_flag   = flagmap
      self._fields_by_option = optionmap

      return self
   # --- end of update (...) ---

   def get_fields_with_flag ( self, flag ):
      """Returns the names of the fields that have the given flag.

      arguments:
      * flag --
      """
      return self._fields_by_flag.get ( flag.lower(), () )
   # --- end of get_fields_with_flag (...) ---

   def get_fields_with_option ( self, option ):
      """Returns a struct with fields that have the given option. The actual
      data type depends on the requested option.

      arguments:
      * option --
      """
      return self._fields_by_option.get ( option, () )
   # --- end of get_field_with_option (...) ---

   def get_fields_with_default_value ( self ):
      """Returns a dict { '<field name>' -> '<default value>' } for all
      fields that have a default value.
      """
      return self.get_fields_with_option ( 'defaults' )

   # --- end of get_fields_with_default_value (...) ---

   def get_fields_with_allowed_values ( self ):
      """Returns a set { <field name> } for all fields that allow only
      certain values.
      """
      return self.get_fields_with_option ( 'allowed_values' )

   # --- end of get_fields_with_allowed_values (...) ---

# --- end of DescriptionFields ---
