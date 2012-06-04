# R overlay --
# Copyright 2006-2012 Gentoo Foundation
# Distributed under the terms of the GNU General Public License v2

class DependencyResolver:

	def __init__ ( self ):
		self.channels  = dict()
		self.listeners = dict()


	def get_listener ():
		new_listener = DependencyResolverListener()
		# register the new listener
		self.listeners [new_listener.ident] = new_listener
		return new_listener

	def get_channel ( readonly=False ):
		# ... TODO
		pass



class DependencyResolverListener:

	def __init__ ( self ):
		self.ident = id ( self )

class DependencyResolverChannel ( DependencyResolverListener ):

	def __init__ ( self, main_resolver, *args ):
		super ( DependencyResolverChannel, self ) . __init__ ( args )
		self._depres_master = main_resolver
