# R overlay -- simple dependency rules
# Copyright 2006-2012 Gentoo Foundation
# Distributed under the terms of the GNU General Public License v2

#import re
import logging

#from roverlay import config
from roverlay.depres import deprule
from roverlay.depres.simpledeprule.reader import SimpleDependencyRuleReader
#from roverlay.depres.simpledeprule.rules import *
from roverlay.depres.simpledeprule.abstractrules import SimpleRule

TMP_LOGGER = logging.getLogger ('simpledeps')

class SimpleDependencyRulePool ( deprule.DependencyRulePool ):

	def __init__ ( self, name, priority=70, filepath=None ):
		"""Initializes a SimpleDependencyRulePool, which is a DependencyRulePool
		specialized in simple dependency rules;
		it offers loading rules from files.

		arguments:
		* name     -- string identifier for this pool
		* priority -- of this pool
		* filepath -- if set and not None: load a rule file directly
		"""
		super ( SimpleDependencyRulePool, self ) . __init__ ( name, priority )

		if not filepath is None:
			self.load_rule_file ( filepath )

	# --- end of __init__ (...) ---

	def add ( self, rule ):
		"""Adds a rule to this pool.
		Its class has to be SimpleIgnoreDependencyRule or derived from it.

		arguments:
		* rule --
		"""
		if isinstance ( rule, SimpleRule ):
			self.rules.append ( rule )
		else:
			raise Exception ( "bad usage (simple dependency rule expected)." )

	# --- end of add (...) ---

	def get_reader ( self ):
		return SimpleDependencyRuleReader ( rule_add=self.add )
	# --- end of get_reader (...) ---

	def load_rule_file ( self, filepath ):
		"""Loads a rule file and adds the read rules to this pool.

		arguments:
		* filepath -- file to read
		"""
		logging.error ( "load_rule_file(***) is deprecated, use get_reader()!" )
		new_rules = SimpleDependencyRuleReader().read_file ( filepath )
		for rule in new_rules:
			self.add ( rule )

	# --- end of load_rule_file (...) ---

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

