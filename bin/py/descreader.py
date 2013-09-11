#!/usr/bin/python
#  Usage: descreader [desc_file...]
#
from __future__ import print_function

import sys

import roverlay.core
import roverlay.rpackage.descriptionreader


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
   D = roverlay.rpackage.descriptionreader.DescriptionReader
   config = setup()

   for desc in D.parse_files ( *sys.argv[1:] ):
      print ( desc )
      

# --- end of main (...) ---


if __name__ == '__main__':
   main()

