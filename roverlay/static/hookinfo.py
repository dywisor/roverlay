# R overlay --
# -*- coding: utf-8 -*-
# Copyright (C) 2013 André Erdmann <dywi@mailerd.de>
# Distributed under the terms of the GNU General Public License;
# either version 2 of the License, or (at your option) any later version.

HOOK_DISABLE = ( False, -1, True, )

_OVERLAY_SUCCESS = ( 'overlay_success', )

# name -> (
#    list|False|None events_to_enable_by_default,
#    int|bool prio,
#    bool is_hidden,
#    ...
# )
#
#  where prio is
#  * None -> automatic assignment when creating links
#  * <0   -> forbid hook usage
#  * >=0  -> use hook with the given priority
#
HOOK_INFO = {
   'skel'                  : HOOK_DISABLE,
   'mux'                   : HOOK_DISABLE,
   'create-metadata-cache' : ( _OVERLAY_SUCCESS, 50, False ),
   'git-commit-overlay'    : ( _OVERLAY_SUCCESS, 80, False ),
   'git-push'              : ( False, 85, False ),
}

get = HOOK_INFO.get

def get_priorities ( _HOOK_INFO=HOOK_INFO ):
   return [
      k[1] for k in _HOOK_INFO.values() if type ( k[1] ) == int and k[1] >= 0
   ]
# --- end of get_priorities (...) ---
