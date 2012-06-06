
import re
import logging



from roverlay.depres import deprule

class SimpleDependencyRule ( deprule.DependencyRule ):

	TMP_LOGGER = logging.getLogger ( 'SimpleDependencyRule' )

	def __init__ ( self, resolving_package, dep_str=None, priority=100 ):
		super ( SimpleDependencyRule, self ) . __init__ ( )
		self.dep_alias = set ()

		self.logger = SimpleDependencyRule.TMP_LOGGER.getChild ( resolving_package )
		self.logger.debug ( "new rule" )

		if dep_str:
			self.logger.debug ( "resolves '" + dep_str + "' now." )
			self.dep_alias.add ( dep_str )

		self.resolving_package = resolving_package

		self.priority = priority


	# --- end of __init__ (...) ---

	def add_resolved ( self, dep_str ):
		self.dep_alias.add ( dep_str )
	# --- end of add_resolved (...) ---

	def matches ( self, dep_env, lowercase=True ):

		if lowercase:
			lower_dep_str = dep_env.dep_str.lower()
			for alias in self.dep_alias:
				if alias.lower() == lower_dep_str:
					self.logger.debug ( "matches '" + lower_dep_str + "'" )
					return self.max_score
		elif dep_env.dep_str in self.dep_alias:
			self.logger.debug ( "matches '" + dep_env.dep_str + "'" )
			return self.max_score

		return 0
	# --- end of matches (...) ---

	def get_dep ( self ):
		return self.resolving_package

	def export_rule ( self ):
		pass

class SimpleDependencyRulePool ( deprule.DependencyRulePool ):

	def __init__ ( self, name, priority=70, filepath=None ):
		super ( SimpleDependencyRulePool, self ) . __init__ ( name, priority )

		if not filepath is None:
			self.load_rule_file ( filepath )
	# --- end of __init__ (...) ---

	def add ( self, rule ):
		if isinstance ( rule, SimpleDependencyRule ):
			self.rules.append ( rule )
		else:
			raise Exception ( "bad usage (simple dependency rule expected)." )
	# --- end of add (...) ---

	def load_rule_file ( self, filepath ):
		reader = SimpleDependencyRuleReader()

		new_rules = reader.read_file ( filepath )
		for rule in new_rules:
			self.add ( rule )

	def export_rules ( self, fh ):
		for rule in self.rules:
			to_write = fh.export_rule()
			if isinstance ( to_write, str ):
				fh.write ( to_write )
			else:
				fh.writelines ( to_write )



class SimpleDependencyRuleReader:

	one_line_separator = re.compile ( '\s+::\s+' )
	multiline_start    = '{'
	multiline_stop     = '}'
	comment_chars      = list ( '#;' )


	def __init__ ( self ):
		pass
	# --- end of __init__  (...) ---

	def read_file ( self, filepath ):
		"""Reads a file that contains SimpleDescriptionRules.

		arguments:
		* filepath -- file to read
		"""

		lineno = 0

		try:
			logging.debug ( "Reading simple dependency rule file " + filepath + "." )
			fh = open ( filepath, 'r' )

			next_rule = None
			rules = list ()

			for line in fh.readlines():
				lineno += 1
				line = line.strip()

				if not line:
					pass

				elif not next_rule is None:
					# in a multiline rule
					if line [0] == SimpleDependencyRuleReader.multiline_stop:
						# end of a multiline rule
						rules.append ( next_rule )
						next_rule = None
					else:
						# new resolved str
						next_rule.add_resolved ( line )

				elif line [0] in SimpleDependencyRuleReader.comment_chars:
					# comment
					pass

				elif line [-1] == SimpleDependencyRuleReader.multiline_start:
					# start of multiline rule
					next_rule = SimpleDependencyRule ( line [:-1].rstrip(), None, 100 )

				else:
					# one line rule?
					rule_str = SimpleDependencyRuleReader.one_line_separator.split ( line, 1 )

					if len ( rule_str ) == 2:
						rules.append (
							SimpleDependencyRule ( rule_str [0], rule_str [1], 90 )
						)
					else:
						logging.error (
							"In " + filepath + ", line " + str ( lineno ) + ": cannot use this line."
						)
				# ---

			if fh: fh.close ()

			logging.info ( filepath + ": read " + str ( len ( rules ) ) + " dependency rules." )

			return rules

		except IOError as ioerr:
			if lineno:
				logging.error ( "Failed to read file " + filepath + " after " + str ( lineno ) + " lines." )
			else:
				logging.error ( "Could not read file " + filepath + "." )
			raise

		# --- end of read_file (...) ---

