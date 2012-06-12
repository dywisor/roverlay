# R overlay -- simple dependency rules
# Copyright 2006-2012 Gentoo Foundation
# Distributed under the terms of the GNU General Public License v2

import re
import logging

from roverlay.depres import deprule

TMP_LOGGER = logging.getLogger ('simpledeps')

class SimpleIgnoreDependencyRule ( deprule.DependencyRule ):
	"""A dependency rule that represents an ignored package in portage."""

	def __init__ ( self, dep_str=None, priority=50 ):
		"""Initializes a SimpleIgnoreDependencyRule.

		arguments:
		* dep_str -- a dependency string that this rule is able to resolve
		* priority -- priority of this rule
		"""
		super ( SimpleIgnoreDependencyRule, self ) . __init__ ( priority )
		self.dep_alias = set ()

		self.logger = TMP_LOGGER.getChild ( 'IGNORE_DEPS' )

		if not dep_str is None:
			self.dep_alias.add ( dep_str )

	# --- end of __init__ (...) ---

	def add_resolved ( self, dep_str ):
		"""Adds an dependency string that should be matched by this rule.

		arguments:
		* dep_str --
		"""
		self.dep_alias.add ( dep_str )
	# --- end of add_resolved (...) ---

	def matches ( self, dep_env, lowercase=True ):
		"""Returns True if this rule matches the given DepEnv, else False.

		arguments:
		* dep_env --
		* lowercase -- if True: be case-insensitive when iterating over all
		               stored dep_strings
		"""

		def logmatch ( score=self.max_score ):
			"""Wrapper function that logs a successful match and
			returns its score.

			arguments:
			* score -- score of this match, defaults to self.max_score
			"""

			self.logger.debug ( "matches %s with score %i and priority %i." %
				( dep_env.dep_str, score, self.priority )
			)
			return score
		# --- end of logmatch (...) ---

		if lowercase:
			#lower_dep_str = dep_env.dep_str.lower()
			for alias in self.dep_alias:
				if alias.lower() == dep_env.dep_str_low:
					return logmatch ()
		elif dep_env.dep_str in self.dep_alias:
			return logmatch ()

		return 0
	# --- end of matches (...) ---

	def get_dep ( self ):
		"""Returns the textual portage package representation of this rule,
		which is None 'cause this is an ignored dependency.
		"""
		return None
	# --- end of get_dep (...) ---

	def export_rule ( self, resolving_to=None ):
		"""Returns this rule as a list of text lines that can be written into
		a file.
		An empty list will be returned if dep_alias has zero length.

		arguments:
		* resolving_to -- portage package that the exported rule should
		                  resolve to, defaults to self.resolving_package or
		                  an ignore keyword such as '!'.
		"""

		alias_count = len ( self.dep_alias )

		retlist = []

		if alias_count:
			if resolving_to is None:
				if hasattr ( self, 'resolving_package'):
					resolving_package = self.resolving_package
				else:
					resolving_package = '!'
			else:
				resolving_package = resolving_to

			# todo hardcoded here
			if alias_count > 1:

				retlist = [ resolving_package + ' {\n' ] + \
					[ "\t%s\n" % alias for alias in self.dep_alias ] + \
					[ '}\n' ]
			else:
				retlist = [
					"%s :: %s\n" % ( resolving_package, self.dep_alias [0] )
				]

		# -- if

		return retlist
	# --- end of export_rule (...) ---


class SimpleDependencyRule ( SimpleIgnoreDependencyRule ):

	def __init__ ( self, resolving_package, dep_str=None, priority=70 ):
		"""Initializes a SimpleDependencyRule. This is
		a SimpleIgnoreDependencyRule extended by a portage package string.

		arguments:
		* resolving package --
		* dep_str --
		* priority --
		"""
		super ( SimpleDependencyRule, self ) . __init__ (
			dep_str=dep_str, priority=priority
		)

		self.resolving_package = resolving_package

		self.logger = TMP_LOGGER.getChild ( resolving_package )

	# --- end of __init__ (...) ---

	def get_dep ( self ):
		"""Returns the textual portage package representation of this rule,
		e.g. 'dev-lang/R'.
		"""
		return self.resolving_package
	# --- end of get_dep (...) ---


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
		if isinstance ( rule, SimpleIgnoreDependencyRule ):
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
	comment_chars      = list ( '#;' )
	# todo: const/config?
	package_ignore     = [ '!' ]


	def __init__ ( self ):
		""" A SimpleDependencyRuleReader reads such rules from a file."""
		pass
	# --- end of __init__  (...) ---

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

				elif not next_rule is None:
					# in a multiline rule

					if line [0] == SimpleDependencyRuleReader.multiline_stop:
						# end of a multiline rule,
						#  add rule to rules and set next_rule to None
						rules.append ( next_rule )
						next_rule = None
					else:
						# new resolved str
						next_rule.add_resolved ( line )

				elif line [0] in SimpleDependencyRuleReader.comment_chars:
					# comment
					#  it is intented that multi line rules cannot contain comments
					pass

				elif line [-1] == SimpleDependencyRuleReader.multiline_start:
					# start of a multiline rule
					portpkg = line [:-1].rstrip()
					if portpkg in SimpleDependencyRuleReader.package_ignore:
						next_rule = SimpleIgnoreDependencyRule ( None, 60 )
					else:
						next_rule = SimpleDependencyRule ( portpkg, None, 70 )

				else:
					# single line rule?
					rule_str = \
						SimpleDependencyRuleReader.one_line_separator.split (line, 1)

					if len ( rule_str ) == 2:
						# is a single line rule

						if rule_str [0] in SimpleDependencyRuleReader.package_ignore:
							rules.append (
								SimpleIgnoreDependencyRule ( rule_str [1], 40 )
							)
						else:
							rules.append (
								SimpleDependencyRule ( rule_str [0], rule_str [1], 50 )
							)
					else:
						logging.error (
							"In %s, line %i : cannot use this line." %
								( filepath, lineno )
						)
				# ---

			if fh: fh.close ()

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
