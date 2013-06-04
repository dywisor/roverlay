# R overlay -- ebuild creation, dependency filter
# -*- coding: utf-8 -*-
# Copyright (C) 2012 André Erdmann <dywi@mailerd.de>
# Distributed under the terms of the GNU General Public License;
# either version 2 of the License, or (at your option) any later version.

"""dependency filter

This module provides one function, dep_allowed, that is used in depres to
filter out redundant dependencies on dev-lang/R.
"""

__all__ = [ 'dep_allowed', ]

def dep_allowed ( dep ):
   """Filters out redundant dependencies on dev-lang/R."""

   if not dep:
      return 0
   elif dep[0] in '|(':
      # compound dep statements "|| ( a b c )", "( a b c )"
      return 1


   # the oldest version of dev-lang/R in portage
   OLDEST_R_VERSION = ( 2, 10, 1 )
#   OLDEST_R_VERSION = config.get (
#      "PORTAGE.lowest_r_version", "2.10.1"
#   ).split ( '.' )

   cat, sep, remainder = dep.partition ( '/' )
   # don't strip leading '!'
   cat = cat.lstrip ( "<>=" )


   if not sep:
      # cannot parse this
      return 2

   elif cat != 'dev-lang':
      # only filtering dev-lang/R
      return 3

   elif '[' in remainder:
      # USE flag requirements, e.g. "dev-lang/R[lapack]"
      return 4

   # result is ${PN}-${PV} or ${PN}-${PV}-${PR}
   pn_or_pnpv, sepa, ver_or_rev = remainder.rpartition ( '-' )

   if not sepa or not pn_or_pnpv:
      return 5 if ver_or_rev != 'R' else 0

   elif pn_or_pnpv [0] != 'R' or (
      len ( pn_or_pnpv ) > 1 and pn_or_pnpv [1] != '-'
   ):
      # only filtering dev-lang/R
      return 6

   elif len ( ver_or_rev ) == 0:
      return 7

   elif ver_or_rev [0] == 'r':
      try:
         pr = int ( ver_or_rev [1:] )
      except ValueError:
         return 8

      pn, sepa, ver_or_rev = pn_or_pnpv.rpartition ( '-' )

   else:
      pn = pn_or_pnpv
      pr = 0

   try:
      pv = tuple ( int (x) for x in ver_or_rev.split ( '.' ) ) + ( pr, )
   except ValueError:
      raise
      return 9

   return 10 if pv > OLDEST_R_VERSION else 0
# --- end of dep_allowed (...) ---
