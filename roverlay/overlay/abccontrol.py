# R overlay -- overlay package, addition control (abc/base)
# -*- coding: utf-8 -*-
# Copyright (C) 2014 André Erdmann <dywi@mailerd.de>
# Distributed under the terms of the GNU General Public License;
# either version 2 of the License, or (at your option) any later version.

"""overlay package, addition control (abstract/base objects)"""

import abc

from abc import abstractmethod, abstractproperty

try:
   from abc import abstractclassmethod
except ImportError:
   from abc import abstractmethod as abstractclassmethod
   from abc import abstractmethod as abstractstaticmethod
else:
   from abc import abstractstaticmethod

import itertools


# __metaclass__/metaclass= workaround
_AbstractObject = abc.ABCMeta ( str("AbstractObject"), ( object, ), {} )

def _gen_bits ( count ):
   yield 0
   for k in range(count):
      yield 2**k
   ##assert k + 1 == count
   yield ( 2**count ) - 1
# --- end of _gen_bits (...) ---



class AdditionControlResult ( object ):
   # for package_info-level checks,
   #  addition control can "recommend" the following actions
   #  (restricted-inclusive-or; priority as listed in descending order,
   #  or, more formal, lower integer > 0 means higher priority (and 0 having
   #  the lowest priority))
   #
   #  Note that any value v with bool(v)==False should be interpreted as
   #  keep-default-behavior.
   #  However, at addition-control-rule level, v==None means "rule does
   #  not care about package", whereas v==PKG_DEFAULT_BEHAVIOR means
   #  "force default behavior".
   #  Currently, there's no difference between None/bool(v)==False,
   #  as addition control is handled by package rules only.
   #
   #
   # force-deny           -- always deny the package
   # deny-replace         -- accept new packages only (**)
   # force-replace        -- always replace existing ebuilds (***)
   # replace-only         -- do not add new packages (**)
   # revbump-on-collision -- forced revbump if an ebuild exists already
   # default-behavior     -- no addition control
   #
   # (**)  in this context, "replace" includes revbump checks
   # (***) does not trigger revbump logic
   #
   # force-deny should not be used in package rules,
   #  because it is inferior to the "do-not-process" action.
   #  (package_info objects have to be kept in memory only to get rejected
   #  in package_dir.add_package(), while "do-not-process" filters them out
   #  immediately)
   # There are two use cases, though:
   # * in package rules: collapsed branches
   #                      (level1 sets force-deny, level2 resets it)
   # * if the control result depends on the package being replaced
   #    (equal to deny-replace, but faster)
   #
   (
      PKG_DEFAULT_BEHAVIOR,
      PKG_FORCE_DENY,
      PKG_DENY_REPLACE,
      PKG_FORCE_REPLACE,
      PKG_REPLACE_ONLY,
      PKG_REVBUMP_ON_COLLISION,
      PKG_ALL,
   ) = _gen_bits(5)


#   PKG_DESCRIPTION_MAP      = {
#      PKG_FORCE_DENY           : 'force-deny',
#      PKG_DENY_REPLACE         : 'deny-replace',
#      PKG_FORCE_REPLACE        : 'force-replace',
#      PKG_REPLACE_ONLY         : 'replace-only',
#      PKG_REVBUMP_ON_COLLISION : 'revbump-on-collision',
#      PKG_DEFAULT_BEHAVIOR     : 'default',
#   }
#
#   PKG_DESCRIPTION_REVMAP   = { v: k for k,v in PKG_DESCRIPTION_MAP.items() }
#

   @classmethod
   def get_effective_package_policy ( cls, pkg_policy ):
      # hardcoded for now

      if not pkg_policy:
         return cls.PKG_DEFAULT_BEHAVIOR

      elif (pkg_policy & ~cls.PKG_ALL):
         raise ValueError("{:#x}: too low/high".format(pkg_policy))

      elif pkg_policy & cls.PKG_FORCE_DENY:
         return cls.PKG_FORCE_DENY

      elif pkg_policy & cls.PKG_DENY_REPLACE:
         if pkg_policy & cls.PKG_REPLACE_ONLY:
            # deny-replace and replace-only => force-deny
            return cls.PKG_FORCE_DENY
         else:
            return cls.PKG_DENY_REPLACE

      elif pkg_policy & cls.PKG_FORCE_REPLACE:
         return pkg_policy & (cls.PKG_FORCE_REPLACE|cls.PKG_REPLACE_ONLY)

      elif pkg_policy & (cls.PKG_REPLACE_ONLY|cls.PKG_REVBUMP_ON_COLLISION):
         return (
            pkg_policy & (cls.PKG_REPLACE_ONLY|cls.PKG_REVBUMP_ON_COLLISION)
         )
      # -- end if

      raise NotImplementedError("{:#x} unmatched".format(pkg_policy))
   # --- end f get_effective_package_policy (...) ---



# --- end of AdditionControlResult ---



class AbstractAdditionControl ( _AbstractObject, AdditionControlResult ):

##   @abstractmethod
##   def get_sub_view ( self, key ):
##      raise NotImplementedError()

   @abstractmethod
   def check_package (
      self, category, package_dir, new_package, old_package_if_any
   ):
      raise NotImplementedError()
