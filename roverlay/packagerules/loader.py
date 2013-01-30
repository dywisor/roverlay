# R overlay -- package rules, package rule loader (from files)
# -*- coding: utf-8 -*-
# Copyright (C) 2013 André Erdmann <dywi@mailerd.de>
# Distributed under the terms of the GNU General Public License;
# either version 2 of the License, or (at your option) any later version.

__all__ = [ 'PackageRulesLoader', ]

class PackageRulesLoader ( object ):
	"""Loads PackageRules from a file."""

	# TODO

	def __init__ ( self, rules ):
		"""Constructor for PackageRulesLoader.

		arguments:
		* rules -- object where new rules will be added to
		            has to implement an "add_rule()" function
		"""
		self.rules = rules
	# --- end of __init__ (...) ---

	def load ( self, rule_file ):
		"""Loads a rule file.

		arguments:
		* rule_file --
		"""
		raise NotImplementedError ( "TODO" )
	# --- end of load (...) ---

# --- end of PackageRulesLoader ---
