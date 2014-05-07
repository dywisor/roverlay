# R overlay -- dependency resolution, dependency types
# -*- coding: utf-8 -*-
# Copyright (C) 2012 André Erdmann <dywi@mailerd.de>
# Distributed under the terms of the GNU General Public License;
# either version 2 of the License, or (at your option) any later version.

"""dependency types"""

# not using a single bool for these two types
# * some dependencies could be resolved as sys and internal ("just resolve it")
# * allows to add other types

# <deptype> ::= 2**k | k in {0,1,2,...}
# try_other indicates that the dep can be checked world-wide (in non-accepting
# rule pools) after unsuccessful resolution
#
try_other = 1
mandatory = 2
external  = 4
internal  = 8
selfdep   = 16

#internal does not imply selfdep
#  external,internal control whether a rule can resolve dependency strings
#  with a deptype of internal/external
#  (or, whether a dep str expects to be resolved as R or system package)
#
#  internal := dependency on a (R) package "internal" to
#   the R package ecosystem - not necessarily hosted by the generated overlay
#  external := dep on a system package
#
#  selfdep  := dependency (the ebuild) is hosted by the created overlay,
#              which allows selfdep validation etc.
#
# => any combination of {external,internal,selfdep} is legal


_MAX = 31

NONE          = 0
RESOLVE_ALL   = external  | internal
ALL           = mandatory | RESOLVE_ALL
MANDATORY_TRY = mandatory | try_other
VIRTUAL       = selfdep   | MANDATORY_TRY

# "system first"
SYS = external | MANDATORY_TRY
# "package first"
PKG = internal | MANDATORY_TRY
