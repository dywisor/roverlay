# R overlay -- roverlay util package, python3-specific functions
# -*- coding: utf-8 -*-
# Copyright (C) 2013 André Erdmann <dywi@mailerd.de>
# Distributed under the terms of the GNU General Public License;
# either version 2 of the License, or (at your option) any later version.

__all__ = [ 'headtail', ]

def headtail ( iterable ):
   head, *tail = iterable
   return ( head, tail )
# --- end of headtail #py3 (...) ---
