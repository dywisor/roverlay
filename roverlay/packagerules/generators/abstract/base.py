# R overlay -- abstract package rule generators
# -*- coding: utf-8 -*-
# Copyright (C) 2014 André Erdmann <dywi@mailerd.de>
# Distributed under the terms of the GNU General Public License;
# either version 2 of the License, or (at your option) any later version.

import abc


# __metaclass__/metaclass= workaround
_AbstractObject = abc.ABCMeta ( str("AbstractObject"), ( object, ), {} )


class AbstractPackageRuleGenerator ( _AbstractObject ):
   """Base class for package rule generators."""

   # declares/implements nothing, currently
   pass
