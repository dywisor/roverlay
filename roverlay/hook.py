# R overlay -- run roverlay hooks (shell scripts)
# -*- coding: utf-8 -*-
# Copyright (C) 2013 André Erdmann <dywi@mailerd.de>
# Distributed under the terms of the GNU General Public License;
# either version 2 of the License, or (at your option) any later version.

import os.path
import logging

import roverlay.config
import roverlay.tools.shenv

__all__ = [ 'run_hook', 'phase_allowed', ]

LOGGER = logging.getLogger ( 'event_hook' )


_EVENT_SCRIPT = None

# None|iterable _EVENT_RESTRICT
_EVENT_RESTRICT = None

# int _EVENT_POLICY
# -1: no policy (allow all)
#  0: not configured
#  1: allow unless in _EVENT_RESTRICT (blacklist)
#  2: deny  unless in _EVENT_RESTRICT (whitelist)
#  4: deny all
_EVENT_POLICY = 0


class HookException ( Exception ):
   pass

def setup():
   global _EVENT_SCRIPT
   global _EVENT_POLICY
   global _EVENT_RESTRICT

   _EVENT_SCRIPT = roverlay.config.get ( 'EVENT_HOOK.exe', False )
   if _EVENT_SCRIPT is False:
      if roverlay.config.get_or_fail ( 'installed' ):
         s = os.path.join (
            roverlay.config.get_or_fail ( 'INSTALLINFO.libexec' ),
            *roverlay.config.get_or_fail ( 'EVENT_HOOK.default_exe_relpath' )
         )
         if os.path.isfile ( s ):
            _EVENT_SCRIPT = s
         else:
            LOGGER.error (
               'missing {!r} - '
               'has roverlay been installed properly?'.format ( s )
            )
      else:
         a_dir = roverlay.config.get ( 'OVERLAY.additions_dir', None )
         if a_dir:
            s = os.path.join (
               a_dir, *roverlay.config.get_or_fail (
                  'EVENT_HOOK.default_exe_relpath'
               )
            )
            if os.path.isfile ( s ):
               _EVENT_SCRIPT = s
      # -- end if installed
   # -- end if _EVENT_SCRIPT

   conf_restrict = roverlay.config.get ( 'EVENT_HOOK.restrict', False )

   if conf_restrict:
      # tristate None,False,True
      is_whitelist = None
      allow = set()
      deny  = set()
      for p in conf_restrict:
         if p in { '*', '+*', '-*' }:
            # "allow all" / "deny all"
            #  to avoid confusion, only one "[+-]*" statement is allowed
            if is_whitelist is None:
               is_whitelist = bool ( p[0] == '-' )
            else:
               raise Exception (
                  'EVENT_HOOK_RESTRICT must not contain more than one '
                  '"*"/"+*"/"-*" statement'
               )
         elif p == '-' or p == '+':
            # empty
            pass
         elif p[0] == '-':
            # deny <k>
            k = p[1:].lower()
            deny.add ( k )
            try:
               allow.remove ( k )
            except KeyError:
               pass
         else:
            # allow <k>
            k = ( p[1:] if p[0] == '+' else p ).lower()
            allow.add ( k )
            try:
               deny.remove ( k )
            except KeyError:
               pass
      # -- end for;

      if is_whitelist is None:
         # allow is set                   => is whitelist
         # neither allow nor deny are set => deny allow
         is_whitelist = bool ( allow or not deny )
      # -- end if is_whitelist #1

      if is_whitelist:
         if allow:
            _EVENT_RESTRICT = frozenset ( allow )
            _EVENT_POLICY   = 2
         else:
            _EVENT_POLICY = 4
      elif deny:
         _EVENT_RESTRICT = frozenset ( deny )
         _EVENT_POLICY   = 1
      else:
         _EVENT_POLICY = -1
      # -- end if is_whitelist #2
   else:
      _EVENT_POLICY = -1
   # -- end if conf_restrict
# --- end of setup (...) ---

def phase_allowed ( phase ):
   if _EVENT_POLICY == -1:
      return True
   elif _EVENT_POLICY == 1:
      # allow unless in restrict
      if phase not in _EVENT_RESTRICT:
         return True
      else:
         LOGGER.debug (
            "phase {!r} denied by blacklist policy.".format ( phase )
         )
   elif _EVENT_POLICY == 2:
      # deny unless in restrict
      if phase in _EVENT_RESTRICT:
         return True
      else:
         LOGGER.debug (
            "phase {!r} denied by whitelist policy.".format ( phase )
         )
   elif _EVENT_POLICY == 4:
      LOGGER.debug (
         "phase {!r} denied by 'deny all' policy".format ( phase )
      )
   else:
      LOGGER.warning (
         "phase {!r} denied by undefined policy {} (fix this)".format (
            phase, _EVENT_POLICY
         )
      )
   # -- end if _EVENT_POLICY

   # default return
   return False
# --- end of phase_allowed (...) ---

def phase_allowed_nolog ( phase ):
   return (
      _EVENT_POLICY == -1
   ) or (
      _EVENT_POLICY == 1 and phase not in _EVENT_RESTRICT
   ) or (
      _EVENT_POLICY == 2 and phase in _EVENT_RESTRICT
   )
# --- end of phase_allowed_nolog (...) ---

def run ( phase, catch_failure=True ):
   if _EVENT_SCRIPT is None:
      LOGGER.warning (
         "hook module not initialized - doing that now (FIXME!)"
      )
      setup()
   # -- end if


   if _EVENT_SCRIPT and phase_allowed ( phase ):
      if roverlay.tools.shenv.run_script (
         _EVENT_SCRIPT, phase, return_success=True
      ):
         return True
      elif catch_failure:
         raise HookException (
            "hook {h!r} returned non-zero for phase {p!r}".format (
               h=_EVENT_SCRIPT, p=phase
            )
         )
         #return False
      else:
         return False
   else:
      # nop
      return True
# --- end of run (...) ---

run_hook = run
