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

   # force-deny           -- always deny the package
   # deny-replace         -- accept new packages only (**)
   # force-replace        -- always replace existing ebuilds (***)
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
   PKG_FORCE_DENY           = 2**0
   PKG_DENY_REPLACE         = 2**1
   PKG_FORCE_REPLACE        = 2**2
   #PKG_REPLACE_ONLY
   PKG_REVBUMP_ON_COLLISION = 2**4
   PKG_DEFAULT_BEHAVIOR     = 0

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
