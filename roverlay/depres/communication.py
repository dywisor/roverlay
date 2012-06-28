# R overlay --
# Copyright 2006-2012 Gentoo Foundation
# Distributed under the terms of the GNU General Public License v2

import threading
import sys

def channel_counter ():
	lock    = threading.Lock()
	last_id = long ( -1 ) if sys.version_info < ( 3, ) else int ( -1 )

	while True:
		with lock:
			last_id += 1
			yield last_id


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

	id_generator = channel_counter()

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
		self.ident          = next ( DependencyResolverChannel.id_generator )
		self._depres_master = main_resolver
	# --- end of __init__ (...) ---

	def set_resolver ( self, resolver, channel_queue=None, **extra ):
		"""Assigns a resolver to this channel.

		arguments:
		* resolver      --
		* channel_queue -- ignored;
		* **extra       -- ignored
		"""
		self._depres_master = resolver
	# --- end of set_resolver (...) ---

	def close ( self ):
		"""Closes this channel."""
		self._depres_master.channel_closed ( self.ident )
		del self._depres_master
	# --- end of close (...) ---

	def enabled ( self ):
		"""Returns True if this channel is enabled, else False."""
		return True
	# --- end of enabled (...) ---
