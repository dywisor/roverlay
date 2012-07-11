import logging

from roverlay import config
from roverlay.depres import deprule

TMP_LOGGER = logging.getLogger ('simpledeps')

class SimpleRule ( deprule.DependencyRule ):
	"""A dependency rule that represents an ignored package in portage."""

	def __init__ ( self,
		dep_str=None, priority=50, resolving_package=None,
		is_selfdep=False, logger_name='simple_rule'
	):
		"""Initializes a SimpleIgnoreDependencyRule.

		arguments:
		* dep_str -- a dependency string that this rule is able to resolve
		* priority -- priority of this rule
		"""
		super ( SimpleRule, self ) . __init__ ( priority )
		self.dep_alias = list()

		self.logger = TMP_LOGGER.getChild ( logger_name )

		self.is_selfdep = is_selfdep

		self.resolving_package = resolving_package

		self.prepare_lowercase_alias = True

		if not dep_str is None:
			self.dep_alias.append ( dep_str )

	# --- end of __init__ (...) ---

	def done_reading ( self ):
		self.dep_alias = frozenset ( self.dep_alias )
		if self.prepare_lowercase_alias:
			self.dep_alias_low = frozenset ( x.lower() for x in self.dep_alias )

	def add_resolved ( self, dep_str ):
		"""Adds an dependency string that should be matched by this rule.

		arguments:
		* dep_str --
		"""
		self.dep_alias.append ( dep_str )
	# --- end of add_resolved (...) ---

	def _find ( self, dep_str, lowercase ):
		if lowercase:
			if hasattr ( self, 'dep_alias_low' ):
				if dep_str in self.dep_alias_low:
					return True

			elif dep_str in ( alias.lower() for alias in self.dep_alias ):
				return True

		return dep_str in self.dep_alias
	# --- end of _find (...) ---

	def matches ( self, dep_env, lowercase=True ):
		"""Returns True if this rule matches the given DepEnv, else False.

		arguments:
		* dep_env --
		* lowercase -- if True: be case-insensitive when iterating over all
		               stored dep_strings
		"""

		if self._find (
			dep_env.dep_str_low if lowercase else dep_env.dep_str, lowercase
		):
			self.logger.debug (
				"matches %s with score %i and priority %i."
					% ( dep_env.dep_str, self.max_score, self.priority )
			)
			return ( self.max_score, self.resolving_package )

		return None
	# --- end of matches (...) ---

	def export_rule ( self ):
		"""Generates text lines for this rule that can later be read using
		the SimpleDependencyRuleReader.
		"""
		# todo hardcoded rule format here
		if self.resolving_package is None:
			resolving = ''
		else:
			resolving = self.resolving_package

			if self.is_selfdep:
				resolving = resolving.split ( '/', 1 ) [1]


		if hasattr ( self.__class__, 'RULE_PREFIX' ):
			resolving = self.__class__.RULE_PREFIX + resolving

		if self.is_selfdep:
			yield resolving

		elif len ( self.dep_alias ) == 0:
			pass

		elif len ( self.dep_alias ) == 1:
			yield "%s :: %s" % ( resolving, iter ( self.dep_alias ).next() )

		else:
			yield resolving + ' {'
			for alias in self.dep_alias:
				yield "\t" + alias
			yield '}'

	def __str__ ( self ):
		return '\n'.join ( self.export_rule() )



class FuzzySimpleRule ( SimpleRule ):

	def __init__ ( self, *args, **kw ):
		super ( FuzzySimpleRule, self ) . __init__ ( *args, **kw )
		self.prepare_lowercase_alias = True

		# 0 : version with modifier, 1 : version w/o mod, 2 : name only, 3 : std
		self.fuzzy_score = ( 1250, 1000, 750, 500 )
		self.max_score   = max ( self.fuzzy_score )

	def matches ( self, dep_env ):
		if self._find ( dep_env.dep_str_low, lowercase=True ):
			# non-fuzzy match
			self.logger.debug (
				"matches %s with score %i and priority %i."
					% ( dep_env.dep_str, self.max_score, self.priority )
			)
			return ( self.fuzzy_score[3], self.resolving_package )

		elif hasattr ( dep_env, 'fuzzy' ):
			for fuzzy in dep_env.fuzzy:
				if 'name' in fuzzy:
					if self._find ( fuzzy ['name'], lowercase=True ):
						# fuzzy match found

						if self.resolving_package is None:
							# ignore rule
							res   = None
							score = self.fuzzy_score [2]


						elif 'version' in fuzzy:

							ver_pkg = '-'.join ( (
								self.resolving_package, fuzzy ['version']
							) )

							vmod = fuzzy ['version_modifier'] \
									if 'version_modifier' in fuzzy \
								else None

							if vmod:
								if '!' in vmod:
									# package matches, but specific version is forbidden
									# ( !<package>-<specific verion> <package> )
									res = '( !=%s %s )' % (
										ver_pkg,
										self.resolving_package
									)

								else:
									# std vmod: >=, <=, =, <, >
									res = vmod + ver_pkg

								score = self.fuzzy_score[0]

							else:
								# version required, but no modifier: defaults to '>='

								res   = '>=' + ver_pkg
								score = self.fuzzy_score[1]

						else:
							# substring match
							#  currently not possible (see DepEnv's regexes)
							score = fuzzy[2]
							res   = self.resolving_package
						# --- if resolving... elif version ... else


						self.logger.debug (
							"fuzzy-match: %s resolved as '%s' with score=%i."
								% ( dep_env.dep_str, res, score )
						)
						return ( score, res )
					# --- if find (=match found)
				# --- if name in
			# --- for fuzzy
		# --- elif hasattr

		return None
	# --- end of matches (...) ---



