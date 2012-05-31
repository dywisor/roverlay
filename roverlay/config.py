# R overlay -- config module
# Copyright 2006-2012 Gentoo Foundation
# Distributed under the terms of the GNU General Public License v2

import sys

from roverlay import descriptionfields

try:
	import configparser
except ImportError:
	import ConfigParser as configparser

def access():
	return ConfigTree() if ConfigTree.instance is None else ConfigTree.instance

class InitialLogger:

	def __init__ ( self ):
		self.debug     = lambda x : sys.stderr.write ( "DBG  " + str ( x ) + "\n" )
		self.info      = lambda x : sys.stderr.write ( "INFO " + str ( x ) + "\n" )
		self.warning   = lambda x : sys.stderr.write ( "WARN " + str ( x ) + "\n" )
		self.error     = lambda x : sys.stderr.write ( "ERR  " + str ( x ) + "\n" )
		self.critical  = lambda x : sys.stderr.write ( "CRIT " + str ( x ) + "\n" )
		self.exception = lambda x : sys.stderr.write ( "EXC! " + str ( x ) + "\n" )

class ConfigTree:
	# static access to the first created ConfigTree
	instance = None

	def __init__ ( self ):
		if ConfigTree.instance is None:
			ConfigTree.instance = self

		self.logger = InitialLogger()

		self.parser = dict()


	def load_field_definition ( self, def_file, lenient=False ):
		if not 'field_def' in self.parser:
			self.parser ['field_def'] = configparser.SafeConfigParser ( allow_no_value=True )

		try:
			self.logger.debug ( "Reading description field definition file " + def_file + "." )
			if lenient:
				self.parser ['field_def'] . read ( def_file )
			else:
				fh = open ( def_file, 'r' )
				self.parser ['field_def'] . readfp ( fh )
				if fh:
					fh.close()
		except IOError as err:
			self.logger.exception ( err )
			raise
		except configparser.MissingSectionHeaderError as mshe:
			self.logger.exception ( mshe )
			raise


