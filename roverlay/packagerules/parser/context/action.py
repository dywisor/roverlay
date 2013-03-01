# R overlay -- package rule parser, action-block context
# -*- coding: utf-8 -*-
# Copyright (C) 2013 André Erdmann <dywi@mailerd.de>
# Distributed under the terms of the GNU General Public License;
# either version 2 of the License, or (at your option) any later version.

import roverlay.strutil

import roverlay.packagerules.actions.evar
import roverlay.packagerules.parser.context.base

class ActionUnknown ( ValueError ):
	pass
# --- end of ActionUnknown ---

class ActionNeedsValue ( ValueError ):
	pass
# --- end of ActionNeedsValue ---


class RuleActionContext (
	roverlay.packagerules.parser.context.base.BaseContext
):
	"""RuleActionContext parses action-blocks."""

	# keywords for the "ignore" action
	KEYWORDS_ACTION_IGNORE = frozenset ((
		'ignore',
		'do-not-process'
	))

	# dict ( <keyword> => <evar class> )
	# Dict of evar action keywords (with corresponding classes)
	#
	KEYWORDS_EVAR = {
		'keywords' : roverlay.packagerules.actions.evar.KeywordsEvarAction,
	}

	def __init__ ( self, namespace ):
		super ( RuleActionContext, self ).__init__ ( namespace )
		self._actions = list()
	# --- end of __init__ (...) ---

	def feed ( self, _str, lino ):
		"""Feeds this action block with input.

		arguments:
		* _str --
		* lino --

		Raises:
		* InvalidContext
		"""
		if _str in self.KEYWORDS_ACTION_IGNORE:
			if not self._actions:
				self._actions = None
			else:
				raise self.InvalidContext (
					"ignore action-block does not accept any other action."
				)
		elif self._actions is None:
			raise self.InvalidContext (
				"ignore action-block does not accept any other action."
			)
		else:
			# split _str into (<keyword>,<value>)
			argv = roverlay.strutil.split_whitespace ( _str, maxsplit=1 )

			evar_cls = self.KEYWORDS_EVAR.get ( argv [0], None )

			try:
				if evar_cls:
					self._actions.append (
						self.namespace.get_object (
							evar_cls,
							roverlay.strutil.unquote ( argv [1] ),
							lino
						)
					)
				else:
					raise ActionUnknown ( _str )

			except IndexError:
				raise ActionNeedsValue ( _str )
	# --- end of feed (...) ---

	def create ( self ):
		"""Returns all created actions."""
		return self._actions
	# --- end of create (...) ---

# --- end of RuleActionContext ---
