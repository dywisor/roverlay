# R overlay --
# Copyright 2006-2012 Gentoo Foundation
# Distributed under the terms of the GNU General Public License v2

import uuid

class DependencyResolverListener ( object ):

	def __init__ ( self ):
		"""
		A DependencyResolverListener listens on events sent by the dep resolver.
		It has no access to the resolver, use DependencyResolverChannel for that.
		"""

		# the identifier must be unique and should not be changed after adding
		# the listener to the dep resolver
		self.ident = id ( self )

		# the event mask is a bit vector used to determine whether
		# the listener accepts or ignores a specific notification
		self.event_mask = 0
	# --- end of __init__ (...) ---

	def accepts ( self, event_type ):
		"""Returns whether this listener modules accepts the given event type.
		This can be used to prevent calculations if no module listens to the
		specific event.

		arguments:
		* event_type --
		"""
		return bool ( self.mask & event_type )
	# --- end of accepts (...) ---

	def notify ( self, event_type, dep_env=None, pkg_env=None, **extra ):
		"""Notify this listener about an event.

		arguments:
		* event_type --
		* dep_env --
		* pkg_env --
		* @kw extra --
		"""
		# stub only
		pass
	# --- end of notify (...) ---


class DependencyResolverChannel ( object ):

	def __init__ ( self, main_resolver ):
		"""Initializes a DependencyResolverChannel which can be used to
		communicate with the dep resolver.

		arguments:
		* main_resolver -- dep resolver to connect to; setting this to None
		                   results in automatic assignment when registering
		                   with the first dep resolver.
		"""
		#super ( DependencyResolverChannel, self ) . __init__ ()
		# channel identifiers must be unique even when the channel has been
		# deleted (id does not guarantee that)
		self.ident          = uuid.uuid4()
		self._depres_master = main_resolver
	# --- end of __init__ (...) ---

	def close ( self ):
		"""Closes this channel."""
		self._depres_master.channel_closed ( self.ident )
	# --- end of close (...) ---

	def enabled ( self ):
		"""Returns True if this channel is enabled, else False."""
		return True
	# --- end of enabled (...) ---
