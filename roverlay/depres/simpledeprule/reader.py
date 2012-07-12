# R overlay -- simple dependency rules
# Copyright 2006-2012 Gentoo Foundation
# Distributed under the terms of the GNU General Public License v2
import os
import sys
import logging

import gzip
import bz2
import mimetypes

from roverlay.depres.simpledeprule.rulemaker import SimpleRuleMaker

class SimpleDependencyRuleReader ( object ):
	"""SimpleDependencyRuleReader is a SimpleRuleMaker frontend for files."""

	def __init__ ( self, rule_add=None ):
		""" A SimpleDependencyRuleReader reads such rules from a file."""
		self.logger = logging.getLogger ( self.__class__.__name__ )

		# note that breakparse is reader-specific (not in SimpleRuleMaker)
		self.breakparse = set (( '#! NOPARSE', '#! BREAK' ))

		self._rmaker = SimpleRuleMaker()

		self._mimetypes = mimetypes.MimeTypes()
		self.guess_ftype = self._mimetypes.guess_type

		self.rule_add = rule_add
	# --- end of __init__  (...) ---

	def read ( self, files_or_dirs ):
		if self.rule_add is None:
			raise AssertionError ( "Rule pool expected, but rule_add is None." )

		for k in files_or_dirs:
			if os.path.isdir ( k ):
				self.read_dir ( k )
			else:
				self.read_file ( k )


	def read_dir ( self, _dir ):
		# without recursion
		for fname in os.listdir ( _dir ):
			f = _dir + os.sep + fname
			if os.path.isfile ( f ):
				self.read_file ( f )
	# --- end of read_dir (...) ---

	def read_file ( self, filepath ):
		"""Reads a file that contains simple dependency rules
		(SimpleIgnoreDependencyRules/SimpleDependencyRules).

		arguments:
		* filepath -- file to read
		"""

		# line number is used for logging
		lineno = 0

		try:
			self.logger.debug (
				"Reading simple dependency rule file %{!r}.".format ( filepath )
			)
			ftype = self.guess_ftype ( filepath )

			compressed = True

			if ftype [1] == 'bzip2':
				fh = bz2.BZ2File ( filepath, mode='r' )
			elif ftype [1] == 'gzip':
				fh = gzip.GzipFile ( filepath, mode='r' )
			else:
				fh = open ( filepath, 'r' )
				compressed = False


			if compressed and sys.version_info >= ( 3, ):
				readlines = ( l.decode().strip() for l in fh.readlines() )
			else:
				readlines = ( l.strip() for l in fh.readlines() )

			for line in readlines:
				lineno += 1

				if not line:
					# empty (the rule maker catches this, too)
					pass

				elif line in self.breakparse:
					# stop reading here
					break

				elif not self._rmaker.add ( line ):
					self.logger.error (
						"In {!r}, line {}: cannot use this line.".format (
							filepath, lineno
						)
					)

			if fh: fh.close()

			rules = self._rmaker.done()

			self.logger.info (
				"{}: read {} dependency rules (in {} lines)".format (
					filepath, len ( rules ), lineno
				)
			)

			if self.rule_add is not None:
				for rule in rules:
					self.rule_add ( rule )
			else:
				return rules

		except IOError as ioerr:
			if lineno:
				self.logger.error (
					"Failed to read file {!r} after {} lines.".format (
						filepath, lineno
					)
				)
			else:
				self.logger.error (
					"Could not read file {!r}.".format ( filepath )
				)
			raise
		finally:
			if 'fh' in locals() and fh: fh.close()

		# --- end of read_file (...) ---
