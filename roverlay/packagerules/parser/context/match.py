# R overlay -- package rule parser, match-block context
# -*- coding: utf-8 -*-
# Copyright (C) 2013 André Erdmann <dywi@mailerd.de>
# Distributed under the terms of the GNU General Public License;
# either version 2 of the License, or (at your option) any later version.

import roverlay.strutil

import roverlay.packagerules.abstract.acceptors
import roverlay.packagerules.parser.context.base
import roverlay.packagerules.acceptors.util

from roverlay.packagerules.acceptors import stringmatch

class EndOfMatchContextError ( Exception ):
	pass
# --- end of EndOfMatchContextError ---

class MatchDepthError ( Exception ):
	def __init__ ( self, our_depth, their_depth ):
		super ( MatchDepthError, self ).__init__ (
			"{} > {}?".format ( their_depth, our_depth )
		)
	# --- end of __init__ (...) ---
# --- end of MatchDepthError ---

class NoSuchMatchStatement ( ValueError ):
	def __init__ ( self, statement, reason ):
		super ( NoSuchMatchStatement, self ).__init__ (
			"{}: {}".format ( statement, reason )
		)
	# --- end of __init__ (...) ---
# --- end of NoSuchMatchStatement ---

class NoSuchMatchOperator ( ValueError ):
	pass
# --- end of NoSuchMatchOperator ---


class RuleMatchContext (
	roverlay.packagerules.parser.context.base.NestableContext
):
	"""RuleMatchContext parses match-blocks."""

	# chars used to indicate the match depth
	MATCH_DEPTH_CHARS = "*-"

	# used to set the "boolean type" of a RuleMatchContext, i.e. which
	# boolean function (acceptor compound class) will be used to combine
	# all read rules
	BOOL_AND  = 0
	BOOL_OR   = 1
	BOOL_XOR1 = 2
	BOOL_NOR  = 3

	# dict ( <bool type> => <acceptor compound class> )
	_BOOL_MAP = {
		BOOL_AND  : roverlay.packagerules.abstract.acceptors.Acceptor_AND,
		BOOL_OR   : roverlay.packagerules.abstract.acceptors.Acceptor_OR,
		BOOL_XOR1 : roverlay.packagerules.abstract.acceptors.Acceptor_XOR1,
		BOOL_NOR  : roverlay.packagerules.abstract.acceptors.Acceptor_NOR,
	}

	# operators used for value comparision
	OP_STRING_EXACT  = frozenset (( '==', '='  ))
	OP_STRING_NOCASE = frozenset (( ',=', '=,' ))
	OP_REGEX_PARTIAL = frozenset (( '~~', '~'  ))
	OP_REGEX_EXACT   = frozenset (( '~=', '=~' ))

	# keywords that introduce a nested match block
	KEYWORDS_AND  = frozenset (( 'and', 'all', '&&' ))
	KEYWORDS_OR   = frozenset (( 'or', 'any', '||' ))
	KEYWORDS_XOR1 = frozenset (( 'xor1', 'xor', '^^' ))
	KEYWORDS_NOR  = frozenset (( 'nor', 'none' ))

	# dict (
	#    keywords => (
	#       <default acceptor class or None >,
	#       <get_value function>
	#    )
	# )
	#
	# None := ExactRegexAcceptor if {"?","*"} in <string> else StringAcceptor
	#
	KEYWORDS_MATCH = {
		'repo' : (
			stringmatch.NocaseStringAcceptor,
			roverlay.packagerules.acceptors.util.get_repo_name,
		),
		'repo_name' : (
			stringmatch.NocaseStringAcceptor,
			roverlay.packagerules.acceptors.util.get_repo_name,
		),
		'package' : (
			None, roverlay.packagerules.acceptors.util.get_package,
		),
		'package_name' : (
			None, roverlay.packagerules.acceptors.util.get_package_name,
		),
		'name' : (
			None, roverlay.packagerules.acceptors.util.get_package_name,
		),
	}

	def __init__ ( self, namespace, level=0, bool_type=None, priority=-1 ):
		"""RuleMatchContext constructor.

		arguments:
		* namespace -- the rule parser's namespace
		* level     -- the depth of this context
		* bool_type -- integer that sets the boolean type of this match
		               context (see BOOL_* above, e.g. BOOL_AND)
		* priority  -- priority of this match block (used for sorting)
		"""
		super ( RuleMatchContext, self ).__init__ (
			namespace = namespace,
			level     = level,
		)

		# match statements defined for this instance (nested ones, e.g. ORed,
		# are in self._nested)
		self._bool_type = (
			bool_type if bool_type is not None else self.BOOL_AND
		)
		self.priority   = priority
		self._matches   = list()
		self._active    = True
	# --- end of __init__ (...) ---

	def _feed ( self, s, match_depth, lino ):
		"""(Actually) feeds a match block with text input, either this one
		(if match_depth is self.level) or a nested one.

		arguments:
		* s           -- preparsed input (a match statement),
		                  whitespace and match depth indicators removed
		* match_depth -- the depth of the match statement
		* lino        -- line number
		"""
		assert match_depth >= self.level

		if not self._active:
			raise EndOfMatchContextError ( "match-block is not active" )

		elif not s:
			pass

		elif match_depth == self.level:
			s_low = s.lower()

			if s_low in self.KEYWORDS_AND:
				self._new_nested ( bool_type=self.BOOL_AND, priority=lino )

			elif s_low in self.KEYWORDS_OR:
				self._new_nested ( bool_type=self.BOOL_OR, priority=lino )

			elif s_low in self.KEYWORDS_XOR1:
				self._new_nested ( bool_type=self.BOOL_XOR1, priority=lino )

			elif s_low in self.KEYWORDS_NOR:
				self._new_nested ( bool_type=self.BOOL_NOR, priority=lino )

			else:
				if self._nested:
					# it's not necessary to mark all (indirect)
					# child RuleMatchContexts as inactive
					self.get_nested()._active = False

				argv = roverlay.strutil.split_whitespace ( s )
				argc = len ( argv )


				match_type = self.KEYWORDS_MATCH.get ( argv [0], None )

				if not match_type:
					raise NoSuchMatchStatement ( argv [0], "unknown" )

				elif argc < 2 or argc > 3:
					raise NoSuchMatchStatement ( s, "invalid arg count" )

				elif argc == 3:
				#elif argc >= 3:
					# <keyword> <op> <arg>

					if argv [1] in self.OP_STRING_EXACT:
						op = stringmatch.StringAcceptor
					elif argv [1] in self.OP_STRING_NOCASE:
						op = stringmatch.NocaseStringAcceptor
					elif argv [1] in self.OP_REGEX_PARTIAL:
						op = stringmatch.RegexAcceptor
					elif argv [1] in self.OP_REGEX_EXACT:
						op = stringmatch.ExactRegexAcceptor
					else:
						raise NoSuchMatchOperator ( argv [1] )

					value = argv [2]

				elif argc == 2:
					# <keyword> <arg>
					#  with op := match_type [0] or <guessed>

					op    = match_type [0]
					value = argv [1]

					if op is None:
						if '*' in value or '?' in value:
							op    = stringmatch.ExactRegexAcceptor
							value = roverlay.strutil.wildcard_to_regex ( value, True )
						else:
							op    = stringmatch.StringAcceptor

				# -- if;

				self._matches.append (
					self.namespace.get_object (
						op,
						lino,
						match_type [1],
						value
					)
				)

		else:
			try:
				return self.get_nested()._feed ( s, match_depth, lino )
			except IndexError:
				raise MatchDepthError ( self.level, match_depth )
	# --- end of _feed (...) ---

	def create ( self ):
		"""Creates and returns an acceptor for this match block."""

		acceptor = self._BOOL_MAP [self._bool_type] ( priority=self.priority )

		for match in self._matches:
			acceptor.add_acceptor ( match )

		for nested in self._nested:
			acceptor.add_acceptor ( nested.create() )

		return acceptor
	# --- end of create (...) ---

	def feed ( self, _str, lino ):
		"""Feeds a match block with input.

		arguments:
		* _str --
		* lino --
		"""
		# prepare _str for the actual _feed() function
		# * determine match depth
		s = _str.lstrip ( self.MATCH_DEPTH_CHARS )
		return self._feed ( s.lstrip(), len ( _str ) - len ( s ), lino )
	# --- end of feed (...) ---

# --- end of RuleMatchContext ---
