# R overlay -- constants (temporary file)
# Copyright 2006-2012 Gentoo Foundation
# Distributed under the terms of the GNU General Public License v2

# matches .tgz .tbz2 .tar .tar.gz .tar.bz2
RPACKAGE_SUFFIX_REGEX = '[.](tgz|tbz2|tar|(tar[.](gz|bz2)))'

PACKAGE_CATEGORY = 'sci-R'

DESCRIPTION_FIELD_SEPARATOR = ':'

DESCRIPTION_COMMENT_CHAR = '#'

DESCRIPTION_LIST_SPLIT_REGEX = '\s*[,;]{1}\s*'

DESCRIPTION_FILE_NAME = 'DESCRIPTION'

DESCRIPTION_VALID_OS_TYPES = [ "unix" ]


# note for 2012-05-25: make this struct more organized, assign real values
"""The map of used fields in the DESCRIPTION file

	stores the real field name as well as field flags and aliases
	that can be case-sensitive (withcase) or not (nocase)

	access to these values is
	* for aliases
		DESCRIPTION_FIELD_MAP [<field name>] [alias] [case sensitive ? withcase : nocase] [<index>]

	* for flags
		DESCRIPTION_FIELD_MAP [<field name>] [flags] [<index>]

	* default values
		DESCRIPTION_FIELD_MAP [<field name>] [default_value]

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
	'Title' : {
		'flags' : [ 'joinValues' ],
	},
	'Package' : {
		'flags' : [ 'joinValues' ],
	},
	'License' : {
		'flags' : [ 'isList' ],
	},
	'Version' : {
		'flags' : [ 'mandatory', 'joinValues' ]
	},
	'Suggests' : {
		'alias' : {
			'nocase' : [ 'Suggests', 'Suggest',
							'%Suggests', 'Suggets', 'Recommends' ]
		},
	},
	'Depends' : {
		'alias' : {
			'nocase' : [ 'Depends', 'Dependencies', 'Dependes',
							'%Depends', 'Depents', 'Require', 'Requires' ],
		},
		'flags' : [ 'isList' ],
		'default_value' : '',
	},
	'Imports' : {
		'alias' : {
			'nocase' : [ 'Imports', 'Import' ]
		},
	},
	'LinkingTo' : {
		'alias' : {
			'nocase' : [ 'LinkingTo', 'LinkingdTo' ]
		},
	},
	'SystemRequirements' : {
		'alias' : {
			'nocase' : [ 'SystemRequirements', 'SystemRequirement' ]
		},
	},
	'OS_Type' : {
		'alias' : {
			'nocase' : [ 'OS_TYPE' ]
		},
	},
	'test-default' : {
		'default_value' : 'some default value'
	}
}
