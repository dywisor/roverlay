# R overlay -- simple dependency rules
# Copyright 2006-2012 Gentoo Foundation
# Distributed under the terms of the GNU General Public License v2

import re
import logging

from roverlay import config

from roverlay.depres import deptype
from roverlay.depres.simpledeprule import rules
from roverlay.depres.simpledeprule.abstractrules import *
from roverlay.depres.simpledeprule.pool import SimpleDependencyRulePool

class SimpleRuleMaker ( object ):
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
		# deptype_kw is '#deptype' (this keyword requires comment 'mode')
		self.deptype_kw      = 'deptype'
		self._deptype        = deptype.ALL
		self._next           = None
		# [ ( deptype, rule ), ... ]
		self._rules          = list()
	# --- end of __init__ (...) ---

	def zap ( self ):
		if self._next is not None:
			self.logger.warning (
				"Multi line rule does not end at EOF - ignored"
			)
		self._next         = None
		self._rules        = list()
	# --- end of zap (...) ---

	def done ( self, as_pool=False ):
		rule_count = len ( self._rules )
		if as_pool:
			poolmap = dict()
			for dtype, rule in self._rules:
				if dtype not in poolmap:
					poolmap [dtype] = SimpleDependencyRulePool (
						name=str ( id ( self ) ),
						deptype_mask=dtype
					)
				poolmap [dtype].add ( rule )
			ret = ( rule_count, tuple ( poolmap.values() ) )
		else:
			ret = self._rules
		self.zap()
		return ret
	# --- end of done (...) ---

	def _get_deptype ( self, t ):
		if len ( t ) == 0 or t == 'all':
			return deptype.ALL
		elif t == 'sys':
			return deptype.external
		elif t == 'pkg':
			return deptype.internal
		else:
			try:
				return int ( t )
			except ValueError:
				return None
	# --- end of _get_deptype (...) ---

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
		self._rules.append ( ( self._deptype, new_rule ) )
		return True
	# --- end of _single_line_rule (...) ---

	def add ( self, line ):
		if len ( line ) == 0:
			return True
		elif self._next is not None:
			if line [0] == self.multiline_stop:
				# end of a multiline rule,
				#  add rule to rules and set next_rule to None
				self._next [1].done_reading()
				self._rules.append ( self._next )
				self._next = None
			else:
				# new resolved str
				self._next [1].add_resolved ( line )

			return True

		elif line [0] == self.comment_char:
			if line [ 1 : 1 + len ( self.deptype_kw ) ] == self.deptype_kw :
				# changing deptype ("#deptype <type>")
				dtype_str = line [ len ( self.deptype_kw ) + 2 : ].lstrip().lower()
				dtype = self._get_deptype ( dtype_str )
				if dtype is not None:
					self._deptype = dtype
				else:
					raise AssertionError (
						"Expected deptype, but got {!r}.".format ( dtype_str )
					)
			# else is a comment,
			#  it's intented that multi line rules cannot contain comments
			return True

		elif len ( line ) > 1 and line [-1] == self.multiline_start:
			l = line [:-1].rstrip()
			rule_class, resolving = self._kw.lookup ( l )

			self._next = (
				self._deptype,
				rule_class ( resolving_package=resolving )
			)
			return True

		else:
			return self._single_line_rule (
				*self.single_line_separator.split ( line, 1  )
			)
	# --- end of add (...) ---
