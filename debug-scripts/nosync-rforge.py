#!/usr/bin/python
#
#  runs --nosync for the R-Forge repo (or first cmdline arg)
#
#  Usage: <prog> [<repo name> [<repo config file>]]
#

import logging

## locate project root directory ("hardcoded" location here)
import sys
import os

PRJ_ROOT = os.path.dirname (
   os.path.dirname ( os.path.abspath ( sys.argv[0] ) )
)
# config file uses relative paths, cd to PRJ_ROOT
os.chdir ( PRJ_ROOT )


## include roverlay modules in PYTHONPATH (add to list head)
sys.path [:0] = [ PRJ_ROOT ]


## repo to (no)sync
get_arg = lambda i, UNSET: sys.argv[i] if len ( sys.argv ) > i else UNSET

REPO_IN_QUESTION = get_arg ( 1, None ) or 'R-Forge'
REPO_CONFIG      = get_arg ( 2, None )


## log everything to console
import roverlay.recipe.easylogger
roverlay.recipe.easylogger.setup_initial ( log_level=logging.DEBUG )
roverlay.recipe.easylogger.freeze_status()


## initialize interface (main and remote)
import roverlay.main
import roverlay.interface.main

MAIN_IF = roverlay.interface.main.MainInterface (
   config_file=roverlay.main.locate_config_file ( False )
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
