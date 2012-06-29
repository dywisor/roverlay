# R overlay -- simple dependency rules
# Copyright 2006-2012 Gentoo Foundation
# Distributed under the terms of the GNU General Public License v2

import re
import logging

from roverlay import config
from roverlay.depres import deprule
from roverlay.depres.abstractsimpledeprule import SimpleRule, FuzzySimpleRule

TMP_LOGGER = logging.getLogger ('simpledeps')

class SimpleIgnoreDependencyRule ( SimpleRule ):

	def __init__ ( self, dep_str=None, priority=50, resolving_package=None ):
		super ( SimpleIgnoreDependencyRule, self ) . __init__ (
			dep_str=dep_str,
			priority=priority,
			resolving_package=None,
			logger_name = 'IGNORE_DEPS',
		)

class SimpleDependencyRule ( SimpleRule ):

	def __init__ ( self, resolving_package, dep_str=None, priority=70 ):
		"""Initializes a SimpleDependencyRule. This is
		a SimpleIgnoreDependencyRule extended by a portage package string.

		arguments:
		* resolving package --
		* dep_str --
		* priority --
		"""
		super ( SimpleDependencyRule, self ) . __init__ (
			dep_str=dep_str,
			priority=priority,
			resolving_package=resolving_package,
			logger_name=resolving_package
		)

	# --- end of __init__ (...) ---

class SimpleFuzzyIgnoreDependencyRule ( FuzzySimpleRule ):

	def __init__ ( self, dep_str=None, priority=51, resolving_package=None ):
		super ( SimpleFuzzyIgnoreDependencyRule, self ) . __init__ (
			dep_str=dep_str,
			priority=priority,
			resolving_package=None,
			logger_name = 'FUZZY.IGNORE_DEPS',
		)

class SimpleFuzzyDependencyRule ( FuzzySimpleRule ):
	def __init__ ( self, resolving_package, dep_str=None, priority=71 ):
		super ( SimpleFuzzyDependencyRule, self ) . __init__ (
			dep_str=dep_str,
			priority=priority,
			resolving_package=resolving_package,
			logger_name = 'FUZZY.' + resolving_package,
		)


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

	def load_rule_file ( self, filepath ):
		"""Loads a rule file and adds the read rules to this pool.

		arguments:
		* filepath -- file to read
		"""
		reader = SimpleDependencyRuleReader()

		new_rules = reader.read_file ( filepath )
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
			to_write = fh.export_rule()
			if isinstance ( to_write, str ):
				fh.write ( to_write )
			else:
				fh.writelines ( to_write )

	# --- end of export_rules (...) ---


class SimpleDependencyRuleReader ( object ):

	one_line_separator = re.compile ( '\s+::\s+' )
	multiline_start    = '{'
	multiline_stop     = '}'
	comment_chars      = "#;"

	# todo: const/config?
	package_ignore = '!'
	fuzzy          = '~'
	fuzzy_ignore   = '%'

	BREAK_PARSING  = frozenset (( '#! NOPARSE', '#! BREAK' ))


	def __init__ ( self ):
		""" A SimpleDependencyRuleReader reads such rules from a file."""
		pass
	# --- end of __init__  (...) ---


	def _make_rule ( self, rule_str ):
		CLS = self.__class__



	def read_file ( self, filepath ):
		"""Reads a file that contains simple dependency rules
		(SimpleIgnoreDependencyRules/SimpleDependencyRules).

		arguments:
		* filepath -- file to read
		"""

		# line number is used for logging
		lineno = 0

		try:
			logging.debug ( "Reading simple dependency rule file %s." % filepath )
			fh = open ( filepath, 'r' )

			CLS = self.__class__

			# the list of read rules
			rules = list ()

			# next rule is set when in a multi line rule (else None)
			next_rule = None

			for line in fh.readlines():
				lineno += 1
				line    = line.strip()

				if not line:
					# empty
					pass

				elif line in CLS.BREAK_PARSING:
					# stop reading here
					break

				elif not next_rule is None:
					# in a multiline rule

					if line [0] == CLS.multiline_stop:
						# end of a multiline rule,
						#  add rule to rules and set next_rule to None
						next_rule.done_reading()
						rules.append ( next_rule )
						next_rule = None
					else:
						# new resolved str
						next_rule.add_resolved ( line )

				elif line [0] in CLS.comment_chars:
					# comment
					#  it is intented that multi line rules cannot contain comments
					pass

				elif line [-1] == CLS.multiline_start:
					# start of a multiline rule
					portpkg = line [:-1].rstrip()

					if portpkg == CLS.fuzzy_ignore:
						next_rule = SimpleFuzzyIgnoreDependencyRule ( None )
					elif portpkg == CLS.fuzzy:
						next_rule = SimpleFuzzyDependencyRule ( portpkg[1:], None )
					elif portpkg == CLS.package_ignore:
						next_rule = SimpleIgnoreDependencyRule ( None, 60 )
					else:
						next_rule = SimpleDependencyRule ( portpkg, None, 70 )

				else:
					# single line rule, either selfdep,
					#  e.g. '~zoo' -> fuzzy sci-R/zoo :: zoo
					#  or normal rule 'dev-lang/R :: R'
					# selfdeps are always single line statements (!)
					rule_str = CLS.one_line_separator.split (line, 1)

					new_rule   = None
					rule_class = None
					resolving  = None

					first_char = rule_str [0][0] if len ( rule_str [0] ) else ''

					if first_char == CLS.fuzzy:
						rule_class = SimpleFuzzyDependencyRule
						resolving  = rule_str [0] [1:]

					elif rule_str [0] == CLS.fuzzy_ignore:
						rule_class = SimpleFuzzyIgnoreDependencyRule
						resolving  = None

					elif rule_str [0] == CLS.package_ignore:
						rule_class = SimpleIgnoreDependencyRule

					else:
						rule_class = SimpleDependencyRule
						resolving  = rule_str [0]

					if len ( rule_str ) == 2:
						# normal rule
						new_rule = rule_class (
							resolving_package=resolving,
							dep_str=rule_str [1]
						)

					elif resolving is not None:
						# selfdep
						dep_str = resolving
						resolving = '/'.join ( (
							config.get_or_fail ( 'OVERLAY.category' ),
							resolving
						) )
						new_rule = rule_class (
							resolving_package=resolving,
							dep_str=dep_str
						)

					# else: error


					if new_rule:
						new_rule.done_reading()
						rules.append ( new_rule )

					else:
						logging.error (
							"In %s, line %i : cannot use this line." %
								( filepath, lineno )
						)
				# ---

			if fh: fh.close ()

			if next_rule is not None:
				logging.warning ( "Multi line rule does not end at EOF - ignored" )

			logging.info (
				"%s: read %i dependency rules (in %i lines)" %
					( filepath, len ( rules ), lineno )
			)

			return rules

		except IOError as ioerr:
			if lineno:
				logging.error (
					"Failed to read file %s after %i lines." % ( filepath, lineno )
				)
			else:
				logging.error ( "Could not read file %s." % filepath )
			raise

		# --- end of read_file (...) ---
