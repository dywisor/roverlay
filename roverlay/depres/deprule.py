# R overlay --
# Copyright 2006-2012 Gentoo Foundation
# Distributed under the terms of the GNU General Public License v2

class DependencyRule:
	def __init__ ( self ):
		self.max_score = 1000

	def matches ( dep_str ):
		return 0

class SimpleDependencyRule ( DependencyRule ):

	def __init__ ( self, resolving_package, dep_str=None, priority=100 ):
		super ( SimpleDependencyRule, self ) . __init__ ( )
		self.dep_alias = set ()
		if dep_str:
			self.dep_alias.add ( dep_str )

		self.resolving_package = resolving_package

		self.priority = priority
	# --- end of __init__ (...) ---

	def add_resolved ( self, dep_str ):
		self.dep_alias.add ( dep_str )
	# --- end of add_resolved (...) ---

	def matches ( self, dep_str, lowercase=True ):
		if lowercase:
			lower_dep_str = dep_str
			for alias in self.dep_alias:
				if alias.lower() == lower_dep_str:
					return self.max_score
		elif dep_str in self.dep_alias:
			return self.max_score

		return 0
	# --- end of matches (...) ---

	def get_dep ( self ):
		return self.resolving_package

	def export_rule ( self ):
		pass

class DependencyRulePool:

	def __init__ ( self, name ):
		self.rules    = list ()
		self.name     = name
		self.priority = 0
	# --- end of __init__ (...) ---

	def sort ( self ):
		self.rules.sort ( key=lambda rule : rule.priority )

		priority_sum = 0
		for r in self.rules:
			priority_sum += r.priority

		self.priority = int ( priority_sum / len ( self.rules ) ) if len ( self.rules ) else 0

		return None
	# --- end of _sort_rules (...) ---

	def add ( self, rule ):
		if issubclass ( rule, DependencyRule ):
			self.rules.append ( rule )
		else:
			raise Exception ( "bad usage (dependency rule expected)." )

		return None
	# --- end of add (...) ---

	def matches ( self, dep_str, skip_matches=0 ):
		"""Tries to find a match in this dependency rule pool.
		The first match is immediatly returned unless skip_matches is != 0, in
		which case the first (>0) / last (<0) skip_matches matches are skipped.

		arguments:
		* dep_str -- dependency to look up
		* skip_matches --
		"""

		if abs ( skip_matches ) >= len ( self.rules ):
			# all matches ignored; cannot expect a result in this case - abort now
			pass

		else:
			skipped = 0
			order = range ( len ( self.rules ) )

			if skip_matches < 1:
				skip_matches *= -1
				order.reverse()

			for index in order:
				score = self.rules [index].matches ( dep_str )
				if score:
					if skipped < skip_matches:
						skipped += 1
					else:
						return score, self.rules [index].get_dep ()


		return 0, None


class SimpleDependencyRulePool ( DependencyRulePool )

	def __init__ ( self, name ):
		super ( SimpleDependencyRulePool, self ) . __init__ ( name )
	# --- end of __init__ (...) ---

	def add ( self, rile ):
		if isinstance ( rule, SimpleDependencyRule ):
			self.rules.append ( rule )
		else:
			raise Exception ( "bad usage (simple dependency rule expected)." )
	# --- end of add (...) ---

	def export_rules ( self, fh ):
		for rule in self.rules:
			to_write = fh.export_rule()
			if isinstance ( to_write, str ):
				fh.write ( to_write )
			else:
				fh.writelines ( to_write )
