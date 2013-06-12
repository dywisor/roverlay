# R overlay -- tools, env for ebuild.py
# -*- coding: utf-8 -*-
# Copyright (C) 2013 André Erdmann <dywi@mailerd.de>
# Distributed under the terms of the GNU General Public License;
# either version 2 of the License, or (at your option) any later version.

import os
import copy
import logging

import roverlay.util

class EbuildEnv ( object ):

   def __init__ ( self, filter_env=True ):
      """Initializes an EbuildEnv.

      arguments:
      * filter_env -- if True: start with an empty env and copy vars
                               from os.environ selectively
                      else   : start with os.environ as env
      """
      self.filter_env    = filter_env
      self.logger        = logging.getLogger ( 'ManifestEnv' )
      self._common_env   = None
   # --- end of __init__ (...) ---

   def add_info ( self, info, **kwargs ):
      self._get_common_env ( True )
      self._common_env.update ( info )
      self._common_env.update ( kwargs )
   # --- end of add_info (...) ---

   def _get_env ( self, additional_info ):
      env = self._get_common_env()
      env.update ( additional_info )
      return env
   # --- end of get_env (...) ---

   def get_distdir_env ( self, distdir ):
      """Returns an onv dict for distdir.

      arguments:
      * distdir --
      """
      return self._get_env ( { 'DISTDIR': distdir } )
   # --- end of get_distdir_env (...) ---

   get_env = get_distdir_env

   def add_overlay_dir ( self, overlay_dir ):
      self._make_common_env()
      self._common_env ['PORTDIR_OVERLAY'] = overlay_dir
   # --- end of add_overlay_dir (...) ---

   def _make_common_env ( self ):
      if self.filter_env:

         # selectively import os.environ
         our_env = roverlay.util.keepenv (
            ( 'PATH', '' ),
            'LANG',
            'PWD',
            'EBUILD_DEFAULT_OPTS'
         )
      else:
         # copy os.environ
         our_env = dict ( os.environ )

      # -- common env part

      # set FEATURES
      # * digest -- needed? (works without it)
      # * assume-digests --
      # * unknown-features-warn -- should FEATURES ever change
      #
      # * noauto -- should prevent ebuild from adding additional actions,
      #   it still tries to download source packages, which is just wrong
      #   here 'cause it is expected that the R package file exists when
      #   calling this function, so FETCHCOMMAND/RESUMECOMMAND will be set
      #   to /bin/true if possible.
      #
      our_env ['FEATURES'] = \
         "noauto digest assume-digests unknown-features-warn"

      self._common_env = our_env
   # --- end of _make_common_env (...) ---

   def _get_common_env ( self ):
      """Creates an environment suitable for an
      "ebuild <ebuild> digest|manifest" call (or uses an already existing env).
      Returns a shallow copy of this env which can then be locally modified
      (setting DISTDIR, PORTAGE_RO_DISTDIRS).
      """

      if self._common_env is None:
         self._make_common_env()

      return copy.copy ( self._common_env )
   # --- end of _get_common_env (...) ---

# --- end of EbuildEnv ---


class FetchEnv ( EbuildEnv ):
   def _make_common_env ( self ):
      super ( FetchEnv, self )._make_common_env()
      # "Cannot chown a lockfile"
      self._common_env ['FEATURES'] += " -distlocks"
   # --- end of _make_common_env (...) ---

# --- end of FetchEnv ---


class ManifestEnv ( EbuildEnv ):
   """per-repo environment container for Manifest creation using ebuild."""

   def _make_common_env ( self ):
      super ( ManifestEnv, self )._make_common_env()

      # set FETCHCOMMAND, RESUMECOMMAND and extend FEATURES:
      # * distlocks -- disabled if FETCHCOMMAND/RESUMECOMMAND set to no-op
      #

      # try to prevent src fetching
      fetch_nop = roverlay.util.sysnop (
         nop_returns_success=True,
         format_str="{nop} \${{DISTDIR}} \${{FILE}} \${{URI}}"
      )

      if not fetch_nop is None:
         self.logger.debug (
            fetch_nop [0] + " disables/replaces FETCHCOMMAND,RESUMECOMMAND."
         )

         self._common_env ['FETCHCOMMAND']  = fetch_nop [1]
         self._common_env ['RESUMECOMMAND'] = fetch_nop [1]
         self._common_env ['FEATURES']     += " -distlocks"
   # --- end of _make_common_env (...) ---

# --- end of ManifestEnv ---
