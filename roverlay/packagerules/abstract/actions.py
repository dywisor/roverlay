# R overlay -- abstract package rules, actions
# -*- coding: utf-8 -*-
# Copyright (C) 2013 André Erdmann <dywi@mailerd.de>
# Distributed under the terms of the GNU General Public License;
# either version 2 of the License, or (at your option) any later version.

__all__ = [ 'PackageRuleAction', ]

class PackageRuleAction ( object ):
	"""PackageRuleActions manipulate PackageInfo instances."""

	def __init__ ( self, priority=1000 ):
		super ( PackageRuleAction, self ).__init__()
		self.priority = priority
		self.logger   = None
	# --- end of __init__ (...) ---

	def set_logger ( self, logger ):
		self.logger = logger
	# --- end of set_logger (...) ---

	def apply_action ( self, p_info ):
		"""Applies the action to the given PackageInfo.

		Returns False if the package should be filtered out.
		Any other value, especially None, should be interpreted as
		"successfully processed"
		(In constrast to the PackageRule.apply_actions(), where any false value
		means "package should be filtered out".)

		arguments:
		* p_info --
		"""
		raise NotImplementedError()
	# --- end of apply_action (...) ---

# --- end of PackageRuleAction ---
