# R overlay -- simple dependency rules, reader
# -*- coding: utf-8 -*-
# Copyright (C) 2012 André Erdmann <dywi@mailerd.de>
# Distributed under the terms of the GNU General Public License;
# either version 2 of the License, or (at your option) any later version.

"""rule reader

This module provides a class, SimpleDependencyRuleReader, that reads dependency
rules from a file.
"""

__all__ = [ 'SimpleDependencyRuleReader', ]

import os
import logging

import roverlay.util

from roverlay.depres.simpledeprule.rulemaker import SimpleRuleMaker

class SimpleDependencyRuleReader ( object ):
   """SimpleDependencyRuleReader is a SimpleRuleMaker frontend for files."""

   def __init__ ( self, pool_add=None, when_done=None ):
      """ A SimpleDependencyRuleReader reads such rules from a file."""
      self.logger = logging.getLogger ( self.__class__.__name__ )

      self._rmaker = SimpleRuleMaker()

      # bind read method of the rule maker
      self.read_file = self._rmaker.read_file

      self._pool_add = pool_add
      self._when_done = when_done

      self._fcount = 0
   # --- end of __init__  (...) ---

   def read ( self, files_or_dirs ):
      """Reads dependency rules from files or directories, in which case
      all files from a dir are read.

      arguments:
      * files_or_dirs --
      """
      if self._pool_add is None:
         raise AssertionError (
            "Read method is for resolver, but pool_add is None."
      )

      for k in files_or_dirs:
         if os.path.isdir ( k ):
            if not roverlay.util.is_vcs_dir ( k ):
               # without recursion
               for fname in os.listdir ( k ):
                  f = k + os.sep + fname
                  if os.path.isfile ( f ):
                     self.read_file ( f )
         else:
            self.read_file ( k )

      rule_count, pools = self._rmaker.done ( as_pool=True )
      self.logger.debug ( "Read {} rules in {} files.".format (
         rule_count, self._fcount
      ) )
      if self._pool_add is not None:
         for p in pools: self._pool_add ( p )

         if self._when_done is not None:
            self._when_done()
      else:
         return pools
   # --- end of read (...) ---
