# R overlay -- recipe, easylogger
# -*- coding: utf-8 -*-
# Copyright (C) 2012 André Erdmann <dywi@mailerd.de>
# Distributed under the terms of the GNU General Public License;
# either version 2 of the License, or (at your option) any later version.

"""sets up logging"""

__all__ = [ 'setup', 'setup_console', 'setup_file', 'setup_initial',
   'setup_initial_console', 'setup_syslog'
]

import sys
import logging
import logging.handlers
import os

_STATUS = 0

ROOT_LOGGER = logging.getLogger()

DEFAULT_DATE_FORMAT = '%F %H:%M:%S'
DEFAULT_STREAM = sys.stdout

def _zap_handlers():
   for h in ROOT_LOGGER.handlers:
      ROOT_LOGGER.removeHandler ( h )
# --- end of _zap_handlers (...) ---

def setup_initial_console():
   ch = logging.StreamHandler ( stream=DEFAULT_STREAM )
   ch.setLevel ( logging.WARN )

   ch.setFormatter (
      logging.Formatter (
         fmt='%(levelname)-7s [%(name)s] %(message)s'
      )
   )

   ROOT_LOGGER.addHandler ( ch )
   ROOT_LOGGER.setLevel ( logging.WARN )
# --- end of setup_initial_console (...) ---

def setup_console ( conf ):
   if not conf.get ( 'LOG.CONSOLE.enabled', False ): return
   stream = conf.get ( 'LOG.CONSOLE.stream', None )

   if stream is not None:
      if stream == 'stderr':
         stream = sys.stderr
      elif stream == 'stdout':
         stream = sys.stdout
      else:
         stream = None

   ch = logging.StreamHandler (
      stream=DEFAULT_STREAM if stream is None else stream
   )

   ch.setLevel (
      conf.get (
         'LOG.CONSOLE.level',
         conf.get ( 'LOG.level', logging.INFO )
      )
   )

   ch_fmt = logging.Formatter (
      fmt=conf.get (
         'LOG.CONSOLE.format',
         '%(levelname)-8s %(name)-14s: %(message)s'
      ),
      datefmt=conf.get ( 'LOG.date_format', DEFAULT_DATE_FORMAT )
   )

   ch.setFormatter ( ch_fmt )

   ROOT_LOGGER.addHandler ( ch )
# --- end of setup_console (...) ---

def setup_syslog ( conf ):
#   if not conf.get ( 'LOG.SYSLOG.enabled', False ): return
#
#   lh = logging.handlers.SysLogHandler()
#
#   lh.setLevel (
#      conf.get (
#         'LOG.SYSLOG.level',
#         conf.get ( 'LOG.level', logging.CRITICAL )
#      )
#   )
#
#   lh_fmt = I_DONT_KNOW
#
#   lh.setFormatter ( lh_fmt )
#
#   ROOT_LOGGER.addHandler ( lh )
#
   pass
# --- end of setup_syslog (...) ---

def setup_file ( conf ):
   logfile = conf.get ( 'LOG.FILE.file' )
   if not logfile or not ( 'LOG.FILE.enabled', True ): return

   rotating = conf.get ( 'LOG.FILE.rotate', False )

   logdir = os.path.dirname ( logfile )
   if not os.path.isdir ( logdir ):
      os.makedirs ( logdir )

   if rotating:
      # using per-run log files

      # rotate after handler creation if log file already exists
      rotate_now = os.path.exists ( logfile )
      fh = logging.handlers.RotatingFileHandler (
         logfile,
         backupCount=conf.get ( 'LOG.FILE.rotate_count', 3 )
      )
      if rotate_now:
         fh.doRollover()
      del rotate_now
   else:
      # using a big log file
      fh = logging.FileHandler ( logfile )

   fh.setLevel (
      conf.get (
         'LOG.FILE.level',
         conf.get ( 'LOG.level', logging.WARN )
      )
   )

   fh_fmt = logging.Formatter (
      fmt=conf.get (
         'LOG.FILE.format',
         '%(asctime)s %(levelname)-8s %(name)-10s: %(message)s'
      ),
      datefmt=conf.get ( 'LOG.date_format', DEFAULT_DATE_FORMAT )
   )

   fh.setFormatter ( fh_fmt )

   if conf.get ( 'LOG.FILE.buffered', True ):
      handler = logging.handlers.MemoryHandler (
         conf.get ( 'LOG.FILE.buffer_capacity', 250 ), # reasonable value?
         target=fh
      )
   else:
      handler = fh

   ROOT_LOGGER.addHandler ( handler )
# --- end of setup_file (...) ---


def setup ( conf ):
   global _STATUS
   if _STATUS > 1:
      return

   _zap_handlers()

   if conf.get ( 'LOG.enabled', True ):
      setup_console ( conf )
      setup_file ( conf )
      #setup_syslog ( conf )


   if not ROOT_LOGGER.handlers:
      # logging is disabled, add a nop handler
      ROOT_LOGGER.addHandler ( logging.NullHandler() )

   ROOT_LOGGER.setLevel ( min ( h.level for h in ROOT_LOGGER.handlers ) )

   _STATUS = 2

def setup_initial():
   global _STATUS
   if _STATUS > 0:
      return

   _zap_handlers()
   logging.lastResort      = None
   logging.raiseExceptions = True
   setup_initial_console()

   _STATUS = 1
