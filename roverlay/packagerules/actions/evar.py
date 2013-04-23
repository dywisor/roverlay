# R overlay -- package rule actions, add/set ebuild variables
# -*- coding: utf-8 -*-
# Copyright (C) 2013 André Erdmann <dywi@mailerd.de>
# Distributed under the terms of the GNU General Public License;
# either version 2 of the License, or (at your option) any later version.

import roverlay.packagerules.abstract.actions

import roverlay.ebuild.evars

__all__ = [
	'EvarAction',
	'KeywordsEvarAction',
]

class EvarAction ( roverlay.packagerules.abstract.actions.PackageRuleAction ):
	"""An EvarAction adds an ebuild variable to a PackageInfo."""

	def __init__ ( self, evar, priority=1000 ):
		"""Constructor for EvarAction.

		arguments:
		* evar     -- ebuild variable that will be added whenever calling
		              apply_action()
		* priority -- priority of this action (used for sorting)
		"""
		super ( EvarAction, self ).__init__ ( priority=priority )
		self._evar = evar
	# --- end of __init__ (...) ---

	def apply_action ( self, p_info ):
		"""Adds the stored ebuild variable to p_info.

		Note:
		 Since the ebuild variable will be added as reference, ebuild creation
		 has to copy it before editing, else *all* ebuilds using this variable
		 will be affected!
		 (At least those that get processed after the evar modification.)

		arguments:
		* p_info --
		"""
		# add ref to self._evar
		p_info.add_evar ( self._evar, unsafe=True )
	# --- end of apply_action (...) ---

	def gen_str ( self, level ):
		yield (
			level * '   ' + self._evar.name.lower()
			+ ' "' + self._evar.value + '"'
		)
	# --- end of gen_str (...) ---

# --- end of EvarAction (...) ---


class KeywordsEvarAction ( EvarAction ):
	"""A KeywordsEvarAction adds a KEYWORDS=... variable to a PackageInfo."""

	def __init__ ( self, keywords, priority=1000 ):
		super ( KeywordsEvarAction, self ).__init__ (
			evar     = roverlay.ebuild.evars.KEYWORDS ( keywords ),
			priority = priority,
		)
	# --- end of __init__ (...) ---

# --- end of KeywordsEvarAction ---
