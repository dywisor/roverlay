#!/usr/bin/python
#
#  runs --nosync for the R-Forge repo (or first cmdline arg)
#
#  Usage: <prog> [<repo name> [<repo config file>]]
#

import sys
import logging

## initialize interface (main and remote)
import roverlay.core
import roverlay.interface.main


def main():
   ## repo to (no)sync
   get_arg = lambda i, UNSET: sys.argv[i] if len ( sys.argv ) > i else UNSET

   REPO_IN_QUESTION = get_arg ( 1, None ) or 'R-Forge'
   REPO_CONFIG      = get_arg ( 2, None )


   ## log everything to console
   roverlay.core.force_console_logging()

   MAIN_IF = roverlay.interface.main.MainInterface (
      config_file=roverlay.core.locate_config_file ( False )
   )


   REPO_IF = MAIN_IF.spawn_interface ( "remote" )
   if REPO_CONFIG:
      REPO_IF.load_repo_file ( REPO_CONFIG )
   else:
      REPO_IF.load_configured()

   REPO_IF.disable_sync()


   ## sync repo and report status
   REPO_IF.sync_named_repo ( REPO_IN_QUESTION, enable_sync=False )

   repo = REPO_IF.get_repo_by_name ( REPO_IN_QUESTION )
   if repo is not None:
      repo_status = repo.sync_status
      repo_ready  = repo.ready()

      print ( "--- snip ---" )
      print ( "repo: " + str ( repo ) )
      if not repo_ready:
         print ( "{n} would be ignored!".format ( n=REPO_IN_QUESTION ) )
      print (
         "{n}.ready() = {r} (sync_status={s:d})".format (
            n=REPO_IN_QUESTION, r=repo_ready, s=repo_status,
         )
      )

   else:
      print ( "no such repo: " + REPO_IN_QUESTION )


   ### switch to python console
   #import code
   #con = code.InteractiveConsole ( locals=locals() )
   #con.interact()
# --- end of main (...) ---

if __name__ == '__main__':
   main()
