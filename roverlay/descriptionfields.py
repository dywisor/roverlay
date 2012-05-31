# R overlay -- description fields
# Copyright 2006-2012 Gentoo Foundation
# Distributed under the terms of the GNU General Public License v2


# split from tmpconst / fileio to make configuration possible, but TODO

class DescriptionField:

	def __init__ ( self, name ):
		if not name:
			raise Exception ( "description field name is empty." )

		self.name = name



	def get_name ( self ):
		return self.name

	def add_flag ( self, flag, lowercase=True ):
		if not hasattr ( self, flags ):
			self.flags = set ()

		self.flags.add ( flag, flag.lower() if lowercase else flag )

		return None


	def del_flag ( self, flag ):
		if hasattr ( self, flags ):
			self.flags.discard ( flag )
		return None


	def add_alias ( self, alias, alias_type='withcase' ):
		if not hasattr ( self, aliases ):
			self.aliases = dict ()

		to_add = dict (
			withcase = alias,
			nocase   = alias.lower(),
		) [alias_type]


		if not alias_type in self.aliases:
			self.aliases [alias_type] = set ()

		self.aliases [alias_type] . add ( to_add )

		return None



	def add_simple_alias ( self, alias, withcase=True ):
		if withcase:
			return self.add_alias ( alias, alias_type='withcase' )
		else:
			return self.add_alias ( alias, alias_type='nocase' )



	def get_default_value ( self ):
		if hasattr ( self, 'default_value' ):
			return self.default_value
		else:
			return None


	def get ( self, key, fallback_value=None ):
		if hasattr ( self, key ):
			return self.key
		else:
			return fallback_value

	def matches ( self, field_identifier ):
		return bool ( self.name == field_identifier ) if field_identifier else False

	def matches_alias ( self, field_identifier ):

		if not field_identifier:
			return False
		if not hasattr ( self, aliases ):
			return False

		if 'withcase' in self.aliases:
			if field_identifier in self.aliases ['withcase']:
				return True

		if 'nocase' in self.aliases:
			field_id_lower = field_identifier.lower()
			if field_id_lower in self.aliases ['nocase']:
				return True

	def has_flag ( self, flag, lowercase=True ):
		if not hasattr ( self, flags ):
			return False

		return bool ( (flag.lower() if lowercase else flag) in self.flags )

class DescriptionFields:

	def __init__ ( self ):
		fields = dict ()

	def add ( self, desc_field ):
		if desc_field:
			if isinstance ( desc_field, DescriptionField ):
				fields [desc_field.get_name()] = desc_field
				return 1
			elif isinstance ( desc_field, str ):
				fields [desc_field] = DescriptionField ( desc_field )
				return 2

		return 0

	def get ( self, field_name ):
		return self.fields [field_name] if field_name in self.fields else None

	# ... TODO

