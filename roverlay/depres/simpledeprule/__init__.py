# R overlay -- simple dependency rules
# -*- coding: utf-8 -*-
# Copyright (C) 2012 André Erdmann <dywi@mailerd.de>
# Distributed under the terms of the GNU General Public License;
# either version 2 of the License, or (at your option) any later version.

"""simple dependency rules

This package implements 'simple' dependency rules. Simple dependency rules
use a dictionary lookups to identify and resolve dependency strings.
"""

__all__ = [ 'SimpleDependencyRulePool', ]

from roverlay.depres.simpledeprule.pool import SimpleDependencyRulePool
