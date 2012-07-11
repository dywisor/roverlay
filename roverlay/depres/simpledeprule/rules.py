# R overlay -- simple dependency rules
# Copyright 2006-2012 Gentoo Foundation
# Distributed under the terms of the GNU General Public License v2
from roverlay.depres.simpledeprule.abstractrules import \
	SimpleRule, FuzzySimpleRule

__all__ = (
	'SimpleIgnoreDependencyRule', 'SimpleDependencyRule',
	'SimpleFuzzyDependencyRule', 'SimpleFuzzyIgnoreDependencyRule'
)

def get_rule_map():
	kwmap = { c.RULE_PREFIX : c for c in (
		SimpleIgnoreDependencyRule,
		SimpleFuzzyDependencyRule,
		SimpleFuzzyIgnoreDependencyRule
	) }

	return ( SimpleDependencyRule, kwmap )
# --- end of get_rule_map (...) ---


class SimpleIgnoreDependencyRule ( SimpleRule ):

	RULE_PREFIX = '!'

	def __init__ ( self, priority=50, resolving_package=None, **kw ):
		super ( SimpleIgnoreDependencyRule, self ) . __init__ (
			logger_name = 'IGNORE_DEPS',
			resolving_package=None,
			priority=50,
			**kw
		)

	def __str__ ( self ):
		if self.is_selfdep:
			return self.__class__.RULE_PREFIX + iter ( self.dep_alias ).next()
		else:
			return super ( self.__class__, self ) . __str__()

class SimpleDependencyRule ( SimpleRule ):

	def __init__ ( self, priority=70, resolving_package=None, **kw ):
		"""Initializes a SimpleDependencyRule. This is
		a SimpleIgnoreDependencyRule extended by a portage package string.

		arguments:
		* resolving package --
		* dep_str --
		* priority --
		"""
		super ( SimpleDependencyRule, self ) . __init__ (
			priority=priority,
			logger_name=resolving_package,
			resolving_package=resolving_package,
			**kw
		)

	# --- end of __init__ (...) ---

class SimpleFuzzyIgnoreDependencyRule ( FuzzySimpleRule ):

	RULE_PREFIX = '%'

	def __init__ ( self, priority=51, resolving_package=None, **kw ):
		super ( SimpleFuzzyIgnoreDependencyRule, self ) . __init__ (
			priority=priority,
			resolving_package=resolving_package,
			logger_name = 'FUZZY.IGNORE_DEPS',
			**kw
		)

	def __str__ ( self ):
		if self.is_selfdep:
			return self.__class__.RULE_PREFIX + iter ( self.dep_alias ).next()
		else:
			return super ( self.__class__, self ) . __str__()

class SimpleFuzzyDependencyRule ( FuzzySimpleRule ):

	RULE_PREFIX = '~'

	def __init__ ( self, priority=71, resolving_package=None, **kw ):
		super ( SimpleFuzzyDependencyRule, self ) . __init__ (
			priority=priority,
			resolving_package=resolving_package,
			logger_name = 'FUZZY.' + resolving_package,
			**kw
		)
