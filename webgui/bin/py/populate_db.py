#!/usr/bin/env python
# -*- coding: utf-8 -*-
# R overlay -- populate example database
# Copyright (C) 2014 André Erdmann <dywi@mailerd.de>
# Distributed under the terms of the GNU General Public License;
# either version 2 of the License, or (at your option) any later version.


"""Imports all configured deprules into the database."""

from __future__ import unicode_literals, absolute_import, print_function

import os
import logging

import roverlay.core
import roverlay.util.fileio




def main():
   roverlay.core.force_console_logging(log_level=logging.INFO)
   config = roverlay.core.load_locate_config_file (
      ROVERLAY_INSTALLED=False, setup_logger=False, load_main_only=True
   )
   iface  = DepruleInterface ( config=config )

   iface.load_configured()
   for model_instance in iface.convert_all_to_models():
      #print ( model_instance.dep_atom_str, model_instance.query_dep_strings() )
      #print(model_instance.match_type)


      pass
   # -- end for

   return

   for pool in rvadmin.adapter.models_to_rule_pools (
      models.SimpleDependencyRule.objects.all()
   ):
      roverlay.util.fileio.write_text_file (
         "/tmp/DRULES/{name}".format ( name=pool.name, addr=id(pool) ),
         pool.export_to_str(),
         compression=None,
      )

# --- end of main (...) ---


if __name__ == '__main__':
   os.environ.setdefault (
      'DJANGO_SETTINGS_MODULE', 'roverlay_webgui.settings'
   )
   import rvcommon.util
   import rvcommon.models
   import rvadmin.adapter
   import rvadmin.models

   from rvcommon.util   import get_or_create_model
   from rvadmin         import models
   from rvadmin.adapter import DepruleInterface
   main()
