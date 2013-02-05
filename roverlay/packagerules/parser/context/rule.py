# R overlay -- package rule parser, rule context
# -*- coding: utf-8 -*-
# Copyright (C) 2013 André Erdmann <dywi@mailerd.de>
# Distributed under the terms of the GNU General Public License;
# either version 2 of the License, or (at your option) any later version.

from roverlay.packagerules.abstract import rules

from . import base, match, action

class RuleContext ( base.NestableContext ):
	"""Class for creating rules from text input (feed(<>)) plus using a few
	control flow functions (end_of_rule(), begin_match(), begin_action()).
	"""

	# CONTEXT_
	#  Used to set/compare the current mode, i.e. how text input will be
	#  interpreted.
	# * CONTEXT_NONE         -- end of the main rule ("self") has been reached
	# * CONTEXT_MATCH        -- set if in a match-block
	# -> CONTEXT_MAIN_MATCH  -- set if in the main match-block
	# -> CONTEXT_SUB_MATCH   -- set if in a nested match-block
	# * CONTEXT_ACTION       -- set if in an action-block
	# -> CONTEXT_MAIN_ACTION -- set if in the main action-block
	# -> CONTEXT_SUB_ACTION  -- set if in a nested action-block
	#
	# * CONTEXT_MAIN -- set if in any main block
	# * CONTEXT_SUB  -- set if in any nested block
	#
	# (use bitwise operators to check against these values)
	#
	CONTEXT_NONE        = 0 # == only
	CONTEXT_MAIN_MATCH  = 1
	CONTEXT_MAIN_ACTION = 2
	CONTEXT_SUB_MATCH   = 4
	CONTEXT_SUB_ACTION  = 8

	CONTEXT_MATCH  = CONTEXT_MAIN_MATCH  | CONTEXT_SUB_MATCH
	CONTEXT_ACTION = CONTEXT_MAIN_ACTION | CONTEXT_SUB_ACTION
	CONTEXT_MAIN   = CONTEXT_MAIN_MATCH  | CONTEXT_MAIN_ACTION
	CONTEXT_SUB    = CONTEXT_SUB_MATCH   | CONTEXT_SUB_ACTION

	# -- end of CONTEXT_ --

	def __init__ ( self, namespace, level=0 ):
		super ( RuleContext, self ).__init__ ( namespace, level )

		self.context         = self.CONTEXT_MAIN_MATCH
		self._match_context  = match.RuleMatchContext   ( self.namespace )
		self._action_context = action.RuleActionContext ( self.namespace )
	# --- end of __init__ (...) ---

	def begin_match ( self ):
		"""Create/begin a match-block of a nested rule.

		Raises: InvalidContext,
		         match-blocks are only allowed within an action-block
		"""
		# nested rules are stored in self._nested (and not in
		# self._action_context where they syntactically belong to)

		if self.context & self.CONTEXT_MAIN_ACTION:
			# a nested rule (with depth = 1)
			self._new_nested()
			self.context = self.CONTEXT_SUB_MATCH
		elif self.context & self.CONTEXT_SUB_ACTION:
			# a nested rule inside a nested one (depth > 1)
			# => redirect to nested
			self.get_nested().begin_match()
			self.context = self.CONTEXT_SUB_MATCH
		else:
			# illegal
			raise self.InvalidContext()
	# --- end of begin_match (...) ---

	def begin_action ( self ):
		"""Create/begin an action block of a rule (nested or "self").

		Raises: InvalidContext,
		         an action-block has to be preceeded by a match-block
		"""
		if self.context & self.CONTEXT_MAIN_MATCH:
			# begin of the main action-block
			self.context = self.CONTEXT_MAIN_ACTION
		elif self.context & self.CONTEXT_SUB_MATCH:
			# action-block of a nested rule
			# => redirect to nested
			self.get_nested().begin_action()
			self.context = self.CONTEXT_SUB_ACTION
		else:
			# illegal
			raise self.InvalidContext()
	# --- end of begin_action (...) ---

	def end_of_rule ( self ):
		"""Has to be called whenever an end-of-rule statement has been reached
		and ends a rule, either this one or a nested one (depending on the
		context).

		Returns True if this rule has been ended, else False (end of a nested
		rule).

		Raises: InvalidContext,
		         rules can only be closed if within an action-block
		"""
		if self.context & self.CONTEXT_MAIN_ACTION:
			# end of this rule
			self.context = self.CONTEXT_NONE
			return True
		elif self.context & self.CONTEXT_SUB_ACTION:
			if self.get_nested().end_of_rule():
				# end of child rule (depth=1)
				self.context = self.CONTEXT_MAIN_ACTION

# no-op, since self.context is already CONTEXT_SUB_ACTION
#			else:
#				# end of a nested rule (depth>1)
#				self.context = self.CONTEXT_SUB_ACTION

			return False
		else:
			raise self.InvalidContext()
	# --- end of end_of_rule (...) ---

	def feed ( self, _str ):
		"""Feed this rule with input (text).

		arguments:
		* _str --

		Raises: InvalidContext if this rule does not accept input
		        (if self.context is CONTEXT_NONE)
		"""
		if self.context & self.CONTEXT_MAIN_MATCH:
			return self._match_context.feed ( _str )
		elif self.context & self.CONTEXT_MAIN_ACTION:
			return self._action_context.feed ( _str )
		elif self.context & self.CONTEXT_SUB:
			return self.get_nested().feed ( _str )
		else:
			raise self.InvalidContext()
	# --- end of feed (...) ---

	def create ( self ):
		"""Rule 'compilation'.

		 Combines all read match- and action-blocks as well as any nested rules
		 into a PackageRule instance (IgnorePackageRule, PackageRule or
		 NestedPackageRule, whatever fits) and returns the result.

		Raises:
		* Exception if the resulting rule is invalid,
		  e.g. no actions/acceptors defined.
		* InvalidContext if end_of_rule has not been reached
		"""
		if self.context != self.CONTEXT_NONE:
			raise self.InvalidContext ( "end_of_rule not reached." )
		# -- if;

		package_rule = None
		actions      = self._action_context.create()
		acceptor     = self._match_context.create()

		if not acceptor:
			raise Exception ( "empty match-block makes no sense." )

		elif len ( self._nested ) > 0:
			# nested rule
			if actions is None:
				raise Exception (
					"ignore action-block cannot contain nested rules."
				)
			else:
				package_rule = rules.NestedPackageRule()
				for nested in self._nested:
					package_rule.add_rule ( nested.create() )

				for action in actions:
					package_rule.add_action ( action )

		elif actions is None:
			# ignore rule
			package_rule = rules.IgnorePackageRule()

		elif actions:
			# normal rule
			package_rule = rules.PackageRule()

			for action in actions:
				package_rule.add_action ( action )

		else:
			raise Exception ( "empty action-block makes no sense." )
		# -- if;

		package_rule.set_acceptor ( acceptor )

		return package_rule
	# --- end of create (...) ---

# --- end of RuleContext ---
