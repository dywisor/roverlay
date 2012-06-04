# R overlay --
# Copyright 2006-2012 Gentoo Foundation
# Distributed under the terms of the GNU General Public License v2

class DependencyRule:
	def __init__ ( self ):
		pass

	def matches ( pkg_env ):
		return False

class SimpleDependencyRule ( DependencyRule ):

	def __init__ ( self, resolving_package, dep_str=None, priority=100 ):
		super ( SimpleDependencyRule, self ) . __init__ ( self )
		self.dep_alias = set ()
		if dep_str:
			self.dep_alias.add ( dep_str )

		self.package = resolving_package

		self.priority = priority
	# --- end of __init__ (...) ---

	def add_resolved ( self, dep_str ):
		self.dep_alias.add ( dep_str )
	# --- end of add_resolved (...) ---

	def matches ( self, pkg_env, lowercase=True ):
		if lowercase:
			lower_dep_str = pkg_env.dep_str
			for alias in self.dep_alias:
				if alias.lower() == lower_dep_str:
					return True
		elif pkg_env.dep_str in self.dep_alias:
			return True

		return False
	# --- end of matches (...) ---

class DependencyRulePool:

	def __init__ ( self ):
		self.rules = list ()
		self._priofunc = lambda x : x.priority
	# --- end of __init__ (...) ---

	def _sort_rules ( self ):
		self.rules.sort ( key=self._priofunc )
		return None
	# --- end of _sort_rules (...) ---

	def add ( self, rule ):
		if issubclass ( rule, DependencyRule ):
			self.rules.add ( rule )
		else:
			raise Exception ( "bad usage (dependency rule expected)." )

		return None
	# --- end of add (...) ---
