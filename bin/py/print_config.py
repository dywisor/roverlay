#!/usr/bin/python
#  Usage: print-config
#
from __future__ import print_function

import sys

import roverlay.core


def setup():
   roverlay.core.force_console_logging()

   config_file = roverlay.core.locate_config_file ( False )
   return roverlay.core.load_config_file (
      config_file, setup_logger=False,
      extraconf={
         'installed': False,
         'DESCRIPTION': { 'descfiles_dir': None, }
      },
   )

# --- end of setup (...) ---


def main():
   config = setup()
   sys.stdout.write ( config.visualize() )
   sys.stdout.flush()
# --- end of main (...) ---


if __name__ == '__main__':
   main()

