
import re
import logging

from roverlay.depres.deprule import SimpleDependencyRule

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
			rules = list ()f

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
				logging.error ( "Failed to read file " + filepath + " after " + str ( lineno ) " lines."
			else:
				logging.error ( "Could not read file " + filepath + "." )
			raise

		# --- end of read_file (...) ---

