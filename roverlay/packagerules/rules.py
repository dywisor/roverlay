# R overlay -- package rules
# -*- coding: utf-8 -*-
# Copyright (C) 2013 André Erdmann <dywi@mailerd.de>
# Distributed under the terms of the GNU General Public License;
# either version 2 of the License, or (at your option) any later version.

__all__ = [ 'PackageRules', ]

import roverlay.packagerules.abstract.rules
import roverlay.packagerules.loader

#import roverlay.packagerules.actions.evar

class PackageRules ( roverlay.packagerules.abstract.rules.NestedPackageRule ):
	"""The top level rule.
	Matches all PackageInfo instances and applies any rule that matches.
	"""

	@classmethod
	def get_configured ( cls ):
		"""Returns a PackageRules instance that uses the configured rules
		(roverlay.config).

		arguments:
		* cls --

		This is a stub since package rule loading is not implemented.
		"""
		rules = PackageRules()
		f = rules.get_loader()
		# "example usage" (just a reminder for PackageRulesLoader)
#		rules.add_action (
#			roverlay.packagerules.actions.evar.KeywordsEvarAction ( "amd64" )
#		)
		return rules
	# --- end of get_configured (...) ---

	def __init__ ( self ):
		super ( PackageRules, self ).__init__ ( priority=-1 )
	# --- end of __init__ (...) ---

	def get_loader ( self ):
		"""Returns a PackageRulesLoader that reads files and adds rules to
		this PackageRules instance.
		"""
		return roverlay.packagerules.loader.PackageRulesLoader ( self )
	# --- end of get_loader (...) ---

	def accepts ( self, p_info ):
		"""Returns True (and therefore doesn't need to be called)."""
		return True
	# --- end of accepts (...) ---

# --- end of PackageRules ---
