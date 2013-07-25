#!/usr/bin/python
#
#  runs roverlay consoles
#

import argparse
import logging

import roverlay.main
import roverlay.recipe.easylogger
import roverlay.console.depres
import roverlay.console.remote

CON_MAP = {
   'depres': roverlay.console.depres.DepresConsole,
   'remote': roverlay.console.remote.RemoteConsole,
}

parser = argparse.ArgumentParser (
   description = "run roverlay consoles",
)

parser.add_argument (
   'mode', choices=frozenset ( CON_MAP ), nargs="?",
   default='depres', help="select console type [%(default)s]",
)

parser.add_argument (
   '--config', '-C', metavar='<file>', dest='config_file',
   default=roverlay.main.locate_config_file ( False ),
   help="config file [%(default)s]",
)

parser.add_argument (
   '--log-all', default=False, action='store_true',
   help="log everything to console",
)

def main():
   arg_config = parser.parse_args()
   con_cls    = CON_MAP [arg_config.mode]

   if arg_config.log_all:
      roverlay.recipe.easylogger.force_reset()
      roverlay.recipe.easylogger.setup_initial ( log_level=logging.DEBUG )
      roverlay.recipe.easylogger.freeze_status()

   with con_cls ( config_file=arg_config.config_file )as con:
      con.run_forever()

if __name__ == '__main__':
   main()
