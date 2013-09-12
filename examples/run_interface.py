#!/usr/bin/python
#
#  initializes logging and roverlay's interfaces
#

import logging

import roverlay.core
import roverlay.interface.main

def main():
   # log everything to console
   roverlay.core.force_console_logging ( log_level=logging.INFO )

   # load roverlay's config
   config = roverlay.core.load_locate_config_file (
      ROVERLAY_INSTALLED=False
   )

   # create the main interface
   main_interface = roverlay.interface.main.MainInterface ( config=config )

   # create subinterfaces, as needed
   depres_interface = main_interface.spawn_interface ( "depres" )
   remote_interface = main_interface.spawn_interface ( "remote" )

   # use them
   pass
# --- end of main (...) ---

if __name__ == '__main__':
   main()
