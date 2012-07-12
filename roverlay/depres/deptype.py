# not using a single bool for these two types
# * some dependencies could be resolved as sys and internal ("just resolve it")
# * allows to add other types

# <deptype> ::= 2**k | k in {0,1,2,...}
# try_call indicates that the dep can be checked world-wide (in non-accepting
# rule pools) after unsuccessful resolution
try_other = 1
mandatory = 2
external  = 4
internal  = 8

ALL = external | internal | mandatory
RESOLVE_ALL = external | internal

SYS = internal | mandatory
PKG = external | mandatory

MANDATORY_TRY = try_other | mandatory
