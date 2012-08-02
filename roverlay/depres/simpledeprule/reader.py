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

	def __init__ ( self, pool_add=None, when_done=None ):
		""" A SimpleDependencyRuleReader reads such rules from a file."""
		self.logger = logging.getLogger ( self.__class__.__name__ )

		# note that breakparse is reader-specific (not in SimpleRuleMaker)
		self.breakparse = set (( '#! NOPARSE', '#! BREAK' ))

		self._rmaker = SimpleRuleMaker()

		self._mimetypes = mimetypes.MimeTypes()
		self.guess_ftype = self._mimetypes.guess_type

		self._pool_add = pool_add
		self._when_done = when_done

		self._fcount = 0

	# --- end of __init__  (...) ---

	def read ( self, files_or_dirs ):
		"""Reads dependency rules from files or directories, in which case
		all files from a dir are read.

		arguments:
		* files_or_dirs --
		"""
		if self._pool_add is None:
			raise AssertionError (
				"Read method is for resolver, but pool_add is None."
		)

		for k in files_or_dirs:
			if os.path.isdir ( k ):
				# without recursion
				for fname in os.listdir ( k ):
					f = k + os.sep + fname
					if os.path.isfile ( f ):
						self.read_file ( f )
			else:
				self.read_file ( k )

		rule_count, pools = self._rmaker.done ( as_pool=True )
		self.logger.debug ( "Read {} rules in {} files.".format (
			rule_count, self._fcount
		) )
		if self._pool_add is not None:
			for p in pools: self._pool_add ( p )

			if self._when_done is not None:
				self._when_done()
		else:
			return pools
	# --- end of read (...) ---

	def read_file ( self, filepath ):
		"""Reads a file that contains simple dependency rules
		(SimpleIgnoreDependencyRules/SimpleDependencyRules).

		arguments:
		* filepath -- file to read
		"""

		# line number is used for logging
		lineno = 0

		self._fcount += 1

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
