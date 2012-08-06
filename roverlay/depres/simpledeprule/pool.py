# R overlay -- simple dependency rules, rule pool
# -*- coding: utf-8 -*-
# Copyright (C) 2012 André Erdmann <dywi@mailerd.de>
# Distributed under the terms of the GNU General Public License;
# either version 2 of the License, or (at your option) any later version.

"""simple dependency rule pool

This module provides a class, SimpleDependencyRulePool, that extends the
usual rule pool by the possibility to export all rules to text/file.
"""

__all__ = [ 'SimpleDependencyRulePool', ]

from roverlay.depres import deprule
from roverlay.depres.simpledeprule.abstractrules import SimpleRule

class SimpleDependencyRulePool ( deprule.DependencyRulePool ):
	def __init__ ( self, name, priority=70, **kw ):
		"""Initializes a SimpleDependencyRulePool, which is a DependencyRulePool
		specialized in simple dependency rules;
		it offers loading rules from files.

		arguments:
		* name     -- string identifier for this pool
		* priority -- of this pool
		"""
		super ( SimpleDependencyRulePool, self ) . __init__ (
			name, priority, **kw
		)
	# --- end of __init__ (...) ---

	def add ( self, rule ):
		"""Adds a rule to this pool.
		Its class has to be SimpleIgnoreDependencyRule or derived from it.

		arguments:
		* rule --
		"""
		# trust in proper usage
		if isinstance ( rule, SimpleRule ):
			self._rule_add ( rule )
		else:
			raise Exception ( "bad usage (simple dependency rule expected)." )
	# --- end of add (...) ---

	def export_rules ( self, fh ):
		"""Exports all rules from this pool into the given file handle.

		arguments:
		* fh -- object that has a writelines ( list ) method

		raises: IOError (fh)
		"""
		for rule in self.rules:
			fh.write ( str ( rule ) )
			fh.write ( '\n' )
	# --- end of export_rules (...) ---
