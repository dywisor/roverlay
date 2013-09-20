# R overlay -- compat module for creating abstract classes (python 3)
# -*- coding: utf-8 -*-
# Copyright (C) 2013 André Erdmann <dywi@mailerd.de>
# Distributed under the terms of the GNU General Public License;
# either version 2 of the License, or (at your option) any later version.

from abc import ABCMeta, abstractmethod

__all__ = [ 'abstractmethod', 'AbstractObject', ]

class AbstractObject ( object, metaclass=ABCMeta ):
   pass
# --- end of AbstractObject ---
