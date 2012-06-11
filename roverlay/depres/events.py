# R overlay -- dependency resolution events
# Copyright 2006-2012 Gentoo Foundation
# Distributed under the terms of the GNU General Public License v2

# uppercase only and values are unique and in { 2**k : int k >= 0 }
DEPRES_EVENTS = dict (
	RESOLVED     = 1,
	UNRESOLVABLE = 2,
	# ...
)
NONE = 0
ALL  = ( 2 ** len ( DEPRES_EVENTS ) ) - 1

def get_eventmask ( *events ):
	"""Returns a mask that allows the given events."""
	mask = NONE
	for ev in events:
		if isinstance ( ev, str ):
			mask |= DEPRES_EVENTS [ev.upper()]
		elif isinstance ( ev, int ):
			mask |= ev
		else:
			raise Exception ( "bad usage" )
	return mask
# --- end of get_eventmask (...) ---

def get_reverse_eventmask ( *events ):
	"""Returns a mask that allows all events but the given ones."""
	mask = ALL
	for ev in events:
		mask &= ~ DEPRES_EVENTS [ev.upper()]
	return mask
# --- end of get_reverse_eventmask (...) ---
