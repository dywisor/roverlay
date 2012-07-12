# R overlay -- simple dependency rules
# Copyright 2006-2012 Gentoo Foundation
# Distributed under the terms of the GNU General Public License v2

import re
import logging

from roverlay import config

#from roverlay.depres import deptype
from roverlay.depres.simpledeprule import rules
from roverlay.depres.simpledeprule.abstractrules import *

class SimpleRuleMaker ( object ):

#	class RuleTypes ( object ): pass

	class RuleKeywords ( object ):
		def __init__ ( self ):
			self._default_rule, self._rule_map = rules.get_rule_map()

		def lookup ( self, keyworded_string ):
			"""Returns <matching rule class>, <keyworded_string without kw>."""
			if len ( keyworded_string ) == 0:
				cls    = self._default_rule
				kwless = None
			else:
				# all keywords have length 1
				kw = keyworded_string [0]
				if kw in self._rule_map:
					cls    = self._rule_map [kw]
					kwless = keyworded_string[1:].lstrip()
					if len ( kwless ) == 0:
						kwless = None
				else:
					cls    = self._default_rule
					kwless = keyworded_string

			return ( cls, kwless )
		# --- end of lookup (...) ---

	def __init__ ( self, rule_separator=None ):
		self.logger = logging.getLogger ( self.__class__.__name__ )

		self.single_line_separator = re.compile (
			'\s+::\s+' if rule_separator is None else rule_separator
		)

		self.multiline_start = '{'
		self.multiline_stop  = '}'
		self.comment_char    = '#'
		self._kw             = self.__class__.RuleKeywords()
		self._next           = None
		self._rules          = list()
		#self._rules         = list() :: ( deptype, rule )
	# --- end of __init__ (...) ---

	def zap ( self ):
		if self._next is not None:
			self.logger.warning (
				"Multi line rule does not end at EOF - ignored"
			)
		self._next         = None
		self._rules        = list()
	# --- end of zap (...) ---

	def done ( self ):
		retrules = self._rules
		self.zap()
		return retrules
	# --- end of done (...) ---

	def _single_line_rule ( self, dep, dep_str='' ):
		# single line rule, either selfdep,
		#  e.g. '~zoo' -> fuzzy sci-R/zoo :: zoo
		#  or normal rule 'dev-lang/R :: R'
		# selfdeps are always single line statements (!)

		rule_class, resolving = self._kw.lookup ( dep )

		if dep_str:
			# normal rule
			new_rule = rule_class (
				resolving_package=resolving,
				dep_str=dep_str,
				is_selfdep=False
			)

		elif resolving is not None:
			# selfdep
			dep_str   = resolving
			resolving = \
				config.get_or_fail ( 'OVERLAY.category' ) + '/' + resolving

			new_rule = rule_class (
				resolving_package=resolving,
				dep_str=dep_str,
				is_selfdep=True
			)
		else:
			return False

		new_rule.done_reading()
		self._rules.append ( new_rule )
		return True
	# --- end of _single_line_rule (...) ---

	def add ( self, line ):
		if len ( line ) == 0:
			return True
		elif self._next is not None:
			if line [0] == self.multiline_stop:
				# end of a multiline rule,
				#  add rule to rules and set next_rule to None
				self._next.done_reading()
				self._rules.append ( self._next )
				self._next = None
			else:
				# new resolved str
				self._next.add_resolved ( line )

			return True

		elif line [0] == self.comment_char:
			# comment
			#  it is intented that multi line rules cannot contain comments
			return True

		elif len ( line ) > 1 and line [-1] == self.multiline_start:
			l = line [:-1].rstrip()
			rule_class, resolving = self._kw.lookup ( l )

			self._next = rule_class ( resolving_package=resolving )
			return True

		else:
			return self._single_line_rule (
				*self.single_line_separator.split ( line, 1  )
			)
	# --- end of add (...) ---
