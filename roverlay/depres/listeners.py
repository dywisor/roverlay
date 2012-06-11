# R overlay -- dep res listeners
# Copyright 2006-2012 Gentoo Foundation
# Distributed under the terms of the GNU General Public License v2

import threading

from roverlay.depres               import events
from roverlay.depres.depenv        import DepEnv
from roverlay.depres.communication import DependencyResolverListener

class FileListener ( DependencyResolverListener ):

	def __init__ ( self, _file, listen_mask ):
		super ( FileListener, self ) . __init__ ()

		self.fh    = None
		self.mask  = listen_mask
		self._file = _file

		if self._file is None:
			raise Exception ("...")
	# --- end of __init__ (...) ---

	def _event ( self, event_type, to_write ):
		if self.mask & event_type:
			if not self.fh: self.fh = open ( self._file, 'a' ) # or w?
			self.fh.write ( to_write + "\n" )
			# when to close? with open (...) as fh:...?
	# --- end of _event (...) ---

	def close ( self ):
		if self.fh: self.fh.close()
	# --- end of close (...) ---


class ResolvedFileListener ( FileListener ):

	def __init__ ( self, _file ):
		super ( ResolvedFileListener, self ) . __init__ (
			_file, events.DEPRES_EVENTS ['RESOLVED']
		)
	# --- end of __init__ (...) ---

	def notify ( self, event_type, dep_env=None, pkg_env=None, **extra ):
		self._event ( event_type,
			"'%s' as '%s'" % ( dep_env.dep_str, dep_env.resolved_by )
		)
	# --- end of notify (...) ---

class UnresolvableFileListener ( FileListener ):
	def __init__ ( self, _file ):
		super ( UnresolvableFileListener, self ) . __init__ (
			_file, events.DEPRES_EVENTS ['UNRESOLVABLE']
		)
	# --- end of __init__ (...) ---

	def notify ( self, event_type, dep_env=None, pkg_env=None, **extra ):
		# <%s> % dep_env.dep_str? TODO
		self._event ( event_type, dep_env.dep_str )
	# --- end of notify (...) ---

