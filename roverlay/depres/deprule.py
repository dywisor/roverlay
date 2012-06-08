# R overlay --
# Copyright 2006-2012 Gentoo Foundation
# Distributed under the terms of the GNU General Public License v2

class DependencyRule ( object ):
	"""Prototype of a dependency rule. Not meant for instantiation."""

	def __init__ ( self, priority ):
		"""Initializes an rule pool.

		arguments:
		* priority -- used for sorting rule pools, lower means more important
		"""
		self.max_score = 1000
		self.priority  = priority
	# --- end of __init__ (...) ---

	def matches ( self, dep_env ):
		"""Returns an int > 0 if this rule matches the given DepEnv."""
		return 0
	# --- end of matches (...) ---

# --- end of DependencyRule ---


class DependencyRulePool ( object ):

	def __init__ ( self, name, priority ):
		"""Initializes an DependencyRulePool, which basically is a set of
		dependency rules with methods like "search for x in all rules."

		arguments:
		* name -- name of this rule pool
		* priority -- priority of this pool (lower is better)
		"""
		self.rules       = list ()
		self.name        = name
		self.priority    = priority
		# the "rule weight" is the sum of the rules' priorities - it's used to
		#  compare/sort dependency pools with the same priority (lesser weight is better)
		self.rule_weight = 0
	# --- end of __init__ (...) ---

	def sort ( self ):
		"""Sorts this rule pool and determines its weight which is used to compare
		rule pools."""

		self.rules.sort ( key=lambda rule : rule.priority )

		rule_priority_sum = 0
		for r in self.rules: rule_priority_sum += r.priority
		self.rule_weight = rule_priority_sum

		return None
	# --- end of sort (...) ---

	def add ( self, rule ):
		"""Adds a DependencyRule to this rule pool.

		arguments:
		* rule --
		"""
		if issubclass ( rule, DependencyRule ):
			self.rules.append ( rule )
		else:
			raise Exception ( "bad usage (dependency rule expected)." )

		return None
	# --- end of add (...) ---

	def matches ( self, dep_env, skip_matches=0 ):
		"""Tries to find a match in this dependency rule pool.
		The first match is immediatly returned unless skip_matches is != 0, in
		which case the first (>0) / last (<0) skip_matches matches are skipped.
		Returns a tuple ( score, portage dependency ),
		e.g. ( 1000, 'sys-apps/which' ), if match found, else None.

		arguments:
		* dep_env -- dependency to look up
		* skip_matches --
		"""

		if abs ( skip_matches ) >= len ( self.rules ):
			# all potential matches ignored,
			#  cannot expect a result in this case - abort now
			pass

		else:
			skipped = 0
			# python3 requires list ( range ... )
			order = list ( range ( len ( self.rules ) ) )

			if skip_matches < 0:
				skip_matches *= -1
				order.reverse()

			for index in order:
				score = self.rules [index].matches ( dep_env )
				if score:
					if skipped < skip_matches:
						skipped += 1
					else:
						return ( score, self.rules [index].get_dep () )


		return None
	# --- end of matches (...) ---
