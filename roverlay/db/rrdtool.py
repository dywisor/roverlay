# R overlay -- stats collection, wrapper for writing rrd databases
# -*- coding: utf-8 -*-
# Copyright (C) 2013 André Erdmann <dywi@mailerd.de>
# Distributed under the terms of the GNU General Public License;
# either version 2 of the License, or (at your option) any later version.

from __future__ import division

# NOT using rrdtool's python bindings as they're available for python 2 only

import logging
import os
import time

import xml.etree.ElementTree

import roverlay.tools.runcmd
from roverlay.tools.runcmd import run_command, run_command_get_output

import roverlay.util
import roverlay.util.objects


class RRDVariable ( object ):

   DST = frozenset ({ 'GAUGE', 'COUNTER', 'DERIVE', 'ABSOLUTE', })

   def __init__ ( self,
      name, val_type, val_min=None, val_max=None, heartbeat=None, step=300,
      heartbeat_factor=2,
   ):
      if val_type not in self.DST:
         raise ValueError ( "invalid DS type: {!r}".format ( val_type ) )

      self.name      = name
      self.val_type  = val_type
      self.val_min   = val_min
      self.val_max   = val_max
      self.heartbeat = heartbeat or ( heartbeat_factor * step )
   # --- end of __init__ (...) ---

   def get_key ( self ):
      mstr = lambda k: 'U' if k is None else str ( k )

      return "DS:{ds_name}:{DST}:{heartbeat}:{vmin}:{vmax}".format (
         ds_name=self.name, DST=self.val_type, heartbeat=self.heartbeat,
         vmin=mstr ( self.val_min ), vmax=mstr ( self.val_max )
      )
   # --- end of get_key (...) ---

   __str__ = get_key

# --- end of RRDVariable ---

class RRDArchive ( object ):

   CF_TYPES = frozenset ({ 'AVERAGE', 'MIN', 'MAX', 'LAST', })

   def __init__ ( self, cf, xff, steps, rows ):
      if cf not in self.CF_TYPES:
         raise ValueError ( "unknown CF: {!r}".format ( cf ) )
      elif not isinstance ( xff, float ):
         raise TypeError ( "xff must be a float." )
      elif xff < 0.0 or xff >= 1.0:
         raise ValueError (
            "xff not in range: 0.0 <= {:f} <= 1.0?".format ( xff )
         )
      elif not isinstance ( steps, int ) or steps <= 0:
         raise ValueError ( "steps must be an integer > 0." )

      elif not isinstance ( rows, int ) or rows <= 0:
         raise ValueError ( "rows must be an integer > 0." )

      self.cf    = cf
      self.xff   = float ( xff )
      self.steps = int ( steps )
      self.rows  = int ( rows )
   # --- end of __init__ (...) ---

   def get_key ( self ):
      return "RRA:{cf}:{xff}:{steps}:{rows}".format (
         cf=self.cf, xff=self.xff, steps=self.steps, rows=self.rows
      )
   # --- end of get_key (...) ---

   __str__ = get_key

   @classmethod
   def _balance_cdp_rows ( cls, step, cdp_time, row_count, min_row_count=2 ):
      my_cdp_time = cdp_time
      my_rows     = row_count
      my_minrows  = min_row_count - 1

      while step > my_cdp_time and my_rows > my_minrows:
         my_cdp_time  *= 2
         my_rows     //= 2

      if step <= my_cdp_time and my_rows > my_minrows:
         return ( my_cdp_time // step, my_rows )
      else:
         raise Exception ( "cannot get steps/rows." )
   # --- end of _balance_cdp_rows (...) ---

   @classmethod
   def get_new ( cls, cf, xff, step, cdp_time, row_count ):
      steps, rows = cls._balance_cdp_rows ( step, cdp_time, row_count )
      return cls ( cf, xff, steps, rows )
   # --- end of get_new (...) ---


   @classmethod
   def new_day ( cls, cf, xff, step=300 ):
      # by default, one CDP per hour (24 rows)
      return cls.get_new ( cf, xff, step, 3600, 24 )
   # --- end of new_day (...) ---

   @classmethod
   def new_week ( cls, cf, xff, step=300 ):
      # one CDP per 6h (28 rows)
      return cls.get_new ( cf, xff, step, 21600, 28 )
   # --- end of new_week (...) ---

   @classmethod
   def new_month ( cls, cf, xff, step=300 ):
      # one CDP per day (31 rows)
      return cls.get_new ( cf, xff, step, 86400, 31 )
   # --- end of new_month (...) ---

# --- end of RRDArchive ---


class RRD ( object ):
   # should be subclassed 'cause _do_create() is not implemented here

   KNOWN_UNKNOWN = frozenset ({ 'u', 'unknown', '-nan', 'nan', })

   RRDTOOL_CMDV_HEAD = ( 'rrdtool', )

   LOGGER = logging.getLogger ( 'RRD' )

   def __init__ ( self, filepath, readonly=False ):
      super ( RRD, self ).__init__()
      self.readonly       = bool ( readonly )
      self.filepath       = filepath
      self._commit_buffer = []
      self._dbfile_exists = False
      self.logger         = self.__class__.LOGGER
      self.INIT_TIME      = self.time_now() - 10
      self.cache          = None
   # --- end of __init__ (...) ---

   def time_now ( self ):
      return int ( time.time() )
   # --- end of time_now (...) ---

   def get_xml_dump ( self ):
      return self._get_rrdtool_output ( "dump" )
   # --- end of get_xml_dump (...) ---

   def _get_rrdtool_output ( self, command, *args ):
      retcode, output = self._call_rrdtool_command (
         command, args, return_success=True, get_output=True
      )
      if retcode == os.EX_OK:
         return output[0]
      else:
         return None
   # --- end of _get_rrdtool_output (...) ---

   def _call_rrdtool_command (
      self, command, args, return_success=True, get_output=False
   ):
      """Creates an arg tuple ( command, <stats db file>, *args ) and
      calls _call_rrdtool() afterwards.
      """
      return self._call_rrdtool (
         ( command, self.filepath, ) + args,
         return_success=return_success, get_output=get_output
      )
   # --- end of _call_rrdtool_command (...) ---

   def _call_rrdtool ( self,
      args, return_success=True, get_output=False, binary_stdout=False
   ):
      cmdv = self.RRDTOOL_CMDV_HEAD + args
      self.logger.info ( "calling rrdtool: {!r}".format ( cmdv ) )

      if get_output:
         cmd_call, output = run_command_get_output (
            cmdv, env=None, binary_stdout=binary_stdout
         )
         if output[1]:
            logger = self.logger.getChild ( 'rrdtool_call' )
            for line in output[1]:
               logger.warning ( line )
         return (
            cmd_call.returncode if return_success else cmd_call, output
         )

      else:
         return run_command (
            cmdv, env=None, logger=self.logger, return_success=return_success
         )
   # --- end of _call_rrdtool (...) ---

   @roverlay.util.objects.abstractmethod
   def _do_create ( self, filepath ):
      pass
   # --- end of _do_create (...) ---

   def check_readonly ( self,
      raise_exception=True, error_msg=None, error_msg_append=True
   ):
      """Verifies that database writing is allowed.

      Returns True if writing is allowed, else False.

      Raises an Exception if the database is readonly and raise_exception
      evaluates to True.
      """
      if self.readonly:
         if raise_exception:
            msg = error_msg
            if error_msg_append:
               if msg:
                  msg += " - database is read-only"
               else:
                  msg = "database is read-only"

            raise Exception ( msg )
         else:
            return False
      else:
         return True
   # --- end of check_readonly (...) ---

   def create_if_missing ( self ):
      if not self._dbfile_exists:
         if os.access ( self.filepath, os.F_OK ):
            self._dbfile_exists = True
         else:
            self.create()
   # --- end of create_if_missing (...) ---

   def create ( self ):
      self.check_readonly()
      roverlay.util.dodir_for_file ( self.filepath )
      self._do_create ( self.filepath )
      if os.access ( self.filepath, os.F_OK ):
         self._dbfile_exists = True
      else:
         raise Exception ( "database file does not exist." )
   # --- end of create (...) ---

   def add ( self, values, timestamp=None ):
      if timestamp is None:
         t = 'N'
      elif timestamp is True:
         t = str ( self.time_now() )
      else:
         t = str ( timestamp )

      self._commit_buffer.append (
         t + ':' + ':'.join ( str(v) for v in values )
      )
   # --- end of add (...) ---

   def clear ( self ):
      self._commit_buffer = []
   # --- end of clear (...) ---

   def commit ( self ):
      self.check_readonly()
      if self._commit_buffer:
         self.create_if_missing()
         self._call_rrdtool (
            ( 'update', self.filepath ) + tuple ( self._commit_buffer )
         )
         self.clear()
   # --- end of commit (...) ---

   def make_cache ( self, mask=-1, clear_cache=False, gauge_type=int ):
      def convert_value ( str_value, value_type ):
         if str_value.lower() in self.KNOWN_UNKNOWN:
            return None
         else:
            try:
               if value_type == 'GAUGE':
                  ret = gauge_type ( str_value )
               elif value_type in { 'COUNTER', 'DERIVE', 'ABSOLUTE' }:
                  ret = int ( str_value )
               else:
                  ret = str_value
            except ValueError:
               return str_value
            else:
               return ret
      # --- end of convert_value (...) ---

      if clear_cache or not self.cache:
         self.cache = dict()

      xml_dump = self.get_xml_dump()
      if not xml_dump:
         return False

      eroot = xml.etree.ElementTree.fromstring ( '\n'.join ( xml_dump ) )

      self.cache ['lastupdate'] = eroot.find ( "./lastupdate" ).text.strip()

      self.cache ['values'] = dict()
      for ds_node in eroot.findall ( "./ds" ):
         ds_name = ds_node.find ( "./name" ).text.strip()
         ds_type = ds_node.find ( "./type" ).text.strip()
         if ds_type != 'COMPUTE':
            ds_value = ds_node.find ( "./last_ds" ).text.strip()
            self.cache ['values'] [ds_name] = convert_value (
               ds_value, ds_type
            )

      return True
   # --- end of make_cache (...) ---

# --- end of RRD ---
