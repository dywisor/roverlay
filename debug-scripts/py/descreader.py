#!/usr/bin/python
#  Usage: descreader [desc_file...]
#
from __future__ import print_function

import sys
import logging

import roverlay
import roverlay.main
import roverlay.recipe.easylogger
import roverlay.rpackage.descriptionreader


def setup():
   roverlay.recipe.easylogger.force_reset()
   roverlay.recipe.easylogger.setup_initial ( log_level=logging.DEBUG )
   roverlay.recipe.easylogger.freeze_status()

   config_file = roverlay.main.locate_config_file ( False )
   return roverlay.load_config_file (
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

