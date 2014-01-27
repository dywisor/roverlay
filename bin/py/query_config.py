#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# See roverlay.scripts.query_config for usage
# or simply run query_config.py --help.
#

import sys

import roverlay.scripts.query_config

if __name__ == '__main__':
   try:
      sys.exit ( roverlay.scripts.query_config.query_config_main ( False ) )
   except KeyboardInterrupt:
      sys.exit ( roverlay.scripts.query_config.EX_IRUPT )
# -- end __main__
