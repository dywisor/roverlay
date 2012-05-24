# R overlay -- constants (temporary file)
# Copyright 2006-2012 Gentoo Foundation
# Distributed under the terms of the GNU General Public License v2

DESCRIPTION_FIELD_SEPARATOR = ':'

DESCRIPTION_COMMENT_CHAR = '#'

DESCRIPTION_LIST_SPLIT_REGEX = '\s*[,;]{1}\s*'

DESCRIPTION_VALID_OS_TYPES = [ "unix" ]


# note for 2012-05-25: make this struct more organized, assign real values
"""The map of used fields in the DESCRIPTION file

	stores the real field name as well as field flags and aliases
	that can be case-sensitive (withcase) or not (nocase)

	access to these values is
	* for aliases
		DESCRIPTION_FIELD_MAP [<field name>] [case sensitive? withcase : nocase] [<index>]

	* for flags
		DESCRIPTION_FIELD_MAP [<field name>] [flags] [<index>]

	notable flags:
	* isList : indicates that this field has several values that are
	           separated by commata/semicolons =:<DESCRIPTION_LIST_SPLIT_REGEX>
	   this disables isWhitespaceList

	* isWhitespaceList : indicates that this field has several values separated
	                     by whitespace

	* joinValues : indicates that the values of this field should be concatenated
	               after reading them (with a ' ' as separator)
	   (this implies that the read values are one string)

	* mandatory : cannot proceed if a file does not contain this field (implies ignoring default values)

"""

DESCRIPTION_FIELD_MAP = {
	'Description' : {
		'flags' : [ 'joinValues' ],
	},
	'Title' : '',
	'Package' : '',
	'License' : '',
	'Suggests' : {
		'nocase' : [ 'Suggests', 'Suggest',
							'%Suggests', 'Suggets', 'Recommends' ]
	},
	'Depends' : {
		'nocase' : [ 'Depends', 'Dependencies', 'Dependes',
							'%Depends', 'Depents', 'Require', 'Requires' ],
		'flags' : [ 'isList', 'mandatory' ],
	},
	'Imports' : {
		'nocase' : [ 'Imports', 'Import' ]
	},
	'LinkingTo' : {
		'nocase' : [ 'LinkingTo', 'LinkingdTo' ]
	},
	'SystemRequirements' : {
		'nocase' : [ 'SystemRequirements', 'SystemRequirement' ]
	},
	'OS_Type' : {
		'nocase' : [ 'OS_TYPE' ]
	}
}
