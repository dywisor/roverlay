# R overlay --
# Copyright 2006-2012 Gentoo Foundation
# Distributed under the terms of the GNU General Public License v2


class DependencyResolver:

	def __init__ ( self ):
		self.logger    = None
		self.channels  = list ()
		self.listeners = list ()


	def _report_event ( self, event, pkg_env=None, **extra ):
		"""Reports an event to the log, channels and listeners."""
		pass


	def set_logmask ( self, logmask ):
		"""Sets the logmask for this DependencyResolver which can be used to
		filter events that would normally go into the log file.
		Useful if a listener module reports such events in an extra file.

		arguments:
		* logmask -- new logmask
		"""
		pass


	def add_listener ( self ):
		"""Adds a listener, which listens to events such as
		"dependency is unresolvable". Possible use cases include redirecting
		such events into a file for further parsing.

		arguments:
		* listener_type
		"""
		new_listener = DependencyResolverListener()
		# register the new listener
		self.listeners [new_listener.ident] = new_listener
		return new_listener

	def get_channel ( self, readonly=False ):
		"""Returns a communication channel to the DependencyResolver.
		This channel can be used to _talk_, e.g. queue dependencies for resolution
		and collect the results later.

		arguments:
		* readonly -- whether this channel has write access or not
		"""
		new channel = DependencyResolverChannel ( self )
		self.channels [new_channel.ident] = new_channel
		return new_channel



class DependencyResolverListener:

	def __init__ ( self ):
		self.ident = id ( self )

	def notify ( event_type, pkg_env=None, **extra ):
		"""Notify this listener about an event."""
		pass


class DependencyResolverChannel ( DependencyResolverListener ):

	def __init__ ( self, main_resolver, *args ):
		super ( DependencyResolverChannel, self ) . __init__ ()
		self._depres_master = main_resolver

	def close ( self ):
		"""Closes this channel."""
		pass


class EbuildJobChannel ( DependencyResolverChannel ):
	def __init__ ( self, main_resolver, *args ):
		super ( EbuildJobChannel, self ) . __init__ ( main_resolver )


	def done ( self ):
		pass

	def add_dependency ( self, dep_str ):
		pass

	def add_dependencies ( self, dep_list ):
		pass

	def satisfy_request ( self ):
		pass

	def lookup ( self, dep_str ):
		return None

