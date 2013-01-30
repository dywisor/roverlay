# R overlay -- abstract package rules, rules
# -*- coding: utf-8 -*-
# Copyright (C) 2013 André Erdmann <dywi@mailerd.de>
# Distributed under the terms of the GNU General Public License;
# either version 2 of the License, or (at your option) any later version.

import roverlay.util

__all__ = [ 'PackageRule', 'NestedPackageRule', 'IgnorePackageRule', ]

class PackageRule ( object ):
	"""A package rule is able to determine whether it matches
	a given PackageInfo instance (using Acceptor instances)
	and applies zero or more actions (using PackageAction instances) to the
	package info.
	"""

	def __init__ ( self, priority=1000 ):
		super ( PackageRule, self ).__init__()
		self.priority   = priority
		self._actions   = list()
		self._acceptors = list()
	# --- end of __init__ (...) ---

	def prepare ( self ):
		"""
		Prepares this rule for usage. Has to be called after adding actions.
		"""
		self._actions   = roverlay.util.priosort ( self._actions )
		self._acceptors = roverlay.util.priosort ( self._acceptors )
		for acceptor in self._acceptors:
			acceptor.prepare()
	# --- end of prepare (...) ---

	def accepts ( self, p_info ):
		"""Returns True if this rule matches the given PackageInfo else False.

		arguments:
		* p_info --
		"""
		for acceptor in self._acceptors:
			if not acceptor.accepts ( p_info ):
				return False
		return True
	# --- end of accepts (...) ---

	def apply_actions ( self, p_info ):
		"""Applies all actions to the given PackageInfo.

		The return value indicates whether the package has been filtered out
		(do not process it any longer -> False) or not (True).

		arguments:
		* p_info -- PackageInfo object that will be modified
		"""
		for action in self._actions:
			# "is False" - see ./actions.py
			if action.apply_action ( p_info ) is False:
				return False
		return True
	# --- end of apply_actions (...) ---

	def add_action ( self, action ):
		"""Adds an action to this rule.

		arguments:
		* action --
		"""
		self._actions.append ( action )
	# --- end of add_action (...) ---

	def add_acceptor ( self, acceptor ):
		"""Adds an acceptor to this rule. Such objects are used to match
		PackageInfo instances (in self.accepts()).

		arguments:
		* acceptor
		"""
		self._acceptors.append ( acceptor )
	# --- end of add_acceptor (...) ---

# --- end of PackageRule ---


class IgnorePackageRule ( PackageRule ):
	"""A rule that has only one action: filter packages."""

	def __init__ ( self, priority=100 ):
		super ( PackageRule, self ).__init__( priority )
	# --- end of __init__ (...) ---

	def apply_actions ( self, p_info ):
		"""Ignores a PackageInfo by returning False.

		arguments:
		* p_info --
		"""
		return False
	# --- end of apply_actions (...) ---

# --- end of IgnorePackageRule ---


class NestedPackageRule ( PackageRule ):
	"""A rule that consists of zero or more subordinate rules."""

	def __init__ ( self, priority=2000 ):
		super ( NestedPackageRule, self ).__init__ ( priority )
		self._rules = list()
	# --- end of __init__ (...) ---

	def prepare ( self ):
		"""
		Prepares this rule for usage. Has to be called after adding actions.
		"""
		super ( NestedPackageRule, self ).prepare()
		self._rules = roverlay.util.priosort ( self._rules )
		for rule in self._rules:
			rule.prepare()
	# --- end of prepare (...) ---

	def apply_actions ( self, p_info ):
		"""Applies all actions to the given PackageInfo.

		The return value indicates whether the package has been filtered out
		(do not process it any longer -> False) or not (True).

		arguments:
		* p_info -- PackageInfo object that will be modified
		"""
		if super ( NestedPackageRule, self ).apply_actions ( p_info ):
			for rule in self._rules:
				if rule.accepts ( p_info ) and not rule.apply_actions ( p_info ):
					return False
			return True
		else:
			return False
	# --- end of apply_actions (...) ---

	def add_rule ( self, rule ):
		"""Adds a rule.

		arguments:
		* rule --
		"""
		self._rules.append ( rule )
	# --- end of add_rule (...) ---

# --- end of NestedPackageRule ---
