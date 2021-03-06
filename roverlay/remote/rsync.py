# R overlay -- remote, rsync
# -*- coding: utf-8 -*-
# Copyright (C) 2012 André Erdmann <dywi@mailerd.de>
# Distributed under the terms of the GNU General Public License;
# either version 2 of the License, or (at your option) any later version.

"""sync packages via rsync"""

__all__ = [ 'RsyncRepo', ]

import os
import sys

from roverlay import config, util

import roverlay.tools.subproc
from roverlay.tools.subproc import create_subprocess as _create_subprocess
from roverlay.tools.subproc import stop_subprocess   as _stop_subprocess
from roverlay.tools.subproc import \
   gracefully_stop_subprocess as _gracefully_stop_subprocess

from roverlay.remote.basicrepo import BasicRepo

RSYNC_ENV = util.keepenv (
   'PATH',
   'USER',
   'LOGNAME',
   'RSYNC_PROXY',
   'RSYNC_PASSWORD',
)

MAX_RSYNC_RETRY = 3

RSYNC_SIGINT = 20

RETRY_ON_RETCODE = frozenset ((
   23, # "Partial transfer due to error"
   24, # "Partial transfer due to vanished source files"
))

# either reraise an KeyboardInterrupt while running rsync (which stops script
# execution unless the interrupt is catched elsewhere) or just set a
# non-zero return code (-> 'repo cannot be used')
RERAISE_INTERRUPT = True

# --recursive is not in the default opts, subdirs in CRAN/contrib are
# either R releases (2.xx.x[-patches]) or the package archive
DEFAULT_RSYNC_OPTS =  (
   '--links',                  # copy symlinks as symlinks,
   '--safe-links',             #  but ignore links outside of tree
   '--times',                  #
#   '--compress',               # .tar.gz ("99%" of synced files) is excluded
                               #  from --compress anyway
   '--dirs',                   #
   '--prune-empty-dirs',       #
#   '--force',                  # allow deletion of non-empty dirs
#   '--delete',                 # --delete is no longer a default opt
   '--human-readable',         #
   '--stats',                  #
   '--chmod=ugo=r,u+w,Dugo+x', # 0755 for transferred dirs, 0644 for files
)

def run_rsync ( cmdv, env=RSYNC_ENV ):
   """Runs an rsync command and terminates/kills the process on error.

   Returns: the command's returncode

   Raises: Passes all exceptions

   arguments:
   * cmdv -- rsync command to (including the rsync executable!)
   * env  -- environment dict, defaults to RSYNC_ENV
   """
   proc = _create_subprocess ( cmdv, env=env )

   try:
      proc.communicate()

   except KeyboardInterrupt:
      sys.stderr.write (
         "\nKeyboard interrupt - waiting for rsync to exit...\n"
      )
      # send SIGTERM and wait,
      #  fall back to _stop_subprocess() if another exception is hit
      _gracefully_stop_subprocess ( proc, stdin=False, kill_timeout_cs=40 )
      raise

   except Exception:
      # send SIGTERM, wait up to 4 seconds before sending SIGKILL
      _stop_subprocess ( proc, kill_timeout_cs=40 )
      raise
   # --

   if proc.returncode == RSYNC_SIGINT:
      raise KeyboardInterrupt ( "propagated from rsync" )

   return proc.returncode
# --- end of run_rsync (...) ----


class RsyncRepo ( BasicRepo ):

   def __init__ (   self,
      name,
      distroot,
      src_uri,
      rsync_uri,
      directory=None,
      recursive=False,
      extra_opts=None
   ):
      """Initializes an RsyncRepo.

      arguments:
      * name       --
      * directory  --
      * src_uri    --
      * rsync_uri  --
      * base_uri   --
      * recursive  -- if '--recursive' should be included in the rsync opts
      * extra_opts -- extra opts for rsync (either None or a tuple/list/..)
      """
      # super's init: name, remote protocol, directory_kw, **uri_kw
      #  using '' as remote protocol which leaves uris unchanged when
      #   normalizing them for rsync usage
      super ( RsyncRepo, self ) . __init__ (
         name=name, distroot=distroot, directory=directory,
         src_uri=src_uri, remote_uri=rsync_uri
      )

      # syncing directories, not files - always appending a slash at the end
      # of remote
      if self.remote_uri [-1] != '/':
         self.remote_uri = self.remote_uri + '/'

      if recursive:
         self.extra_opts = [ '--recursive' ]
         if extra_opts:
            self.extra_opts.extend ( extra_opts )
      else:
         self.extra_opts = extra_opts
   # --- end of __init__ (...) ---

   def _rsync_argv ( self ):
      """Returns an rsync command used for syncing."""
      argv = [ 'rsync' ]

      argv.extend ( DEFAULT_RSYNC_OPTS )

      max_bw = config.get ( 'REPO.rsync_bwlimit', None )
      if max_bw is not None:
         argv.append ( '--bwlimit=' + str ( max_bw ) )

      if self.extra_opts:
         argv.extend ( self.extra_opts )

      argv.extend ( ( self.remote_uri, self.distdir ) )

      # remove empty args from argv
      return [ arg for arg in argv if arg ]
   # --- end of _rsync_argv (...) ---

   def _dosync ( self ):
      """Syncs this repo. Returns True if sync succeeded, else False.
      All exceptions(?) are catched and interpreted as sync failure.
      """
      assert os.EX_OK not in RETRY_ON_RETCODE

      rsync_cmd = self._rsync_argv()
      retcode   = None
      try:
         util.dodir ( self.distdir, mkdir_p=True )
         self.logger.debug ( 'running rsync cmd: ' + ' '.join ( rsync_cmd ) )

         retcode = run_rsync ( rsync_cmd )

         if retcode in RETRY_ON_RETCODE:
            for retry_count in range ( MAX_RSYNC_RETRY ):
               # this handles retcodes like
               #  * 24: "Partial transfer due to vanished source files"

               self.logger.warning (
                  "rsync returned {ret!r}, retrying ({now}/{_max})".format (
                     ret=retcode, now=retry_count, _max=MAX_RSYNC_RETRY
                  )
               )

               retcode = run_rsync ( rsync_cmd )
               if retcode not in RETRY_ON_RETCODE: break
         # -- end if <want retry>

      except KeyboardInterrupt:
         retcode = RSYNC_SIGINT
         if RERAISE_INTERRUPT: raise

      except Exception as e:
         # catch exceptions, log them and return False
         retcode = None
         self.logger.exception ( e )
      # --

      if retcode == os.EX_OK:
         return True
      else:
         self.logger.error (
            'Repo {name} cannot be used for ebuild creation due to errors '
            'while running rsync (return code was {ret}).'.format (
               name=self.name, ret=retcode
         ) )
         return False
   # --- end of _dosync (...) ---
