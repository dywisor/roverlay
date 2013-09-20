#!/bin/sh
# -*- coding: utf-8 -*-
# R overlay -- shell functions, interactive setup for roverlay
# Copyright (C) 2013 André Erdmann <dywi@mailerd.de>
# Distributed under the terms of the GNU General Public License;
# either version 2 of the License, or (at your option) any later version.
#
#
# --- functions provided by this file ---
#
# @private int setup_interactive__read_input (...)
# void roverlay_setup_main ( *args, **ROVERLAY_INSTALLED? ), raises die()
#
# --- variables provided by this file ---
#
# ROVERLAY_SETUP
#
# @private __HAVE_SETUP_INTERACTIVE_FUNCTIONS__
#
# --- END HEADER ---

if [ -z "${__HAVE_SETUP_INTERACTIVE_FUNCTIONS__-}" ]; then

readonly __HAVE_SETUP_INTERACTIVE_FUNCTIONS__=y

if [ -z "${ROVERLAY_SETUP-}" ]; then
   ROVERLAY_SETUP=$(which roverlay-setup 2>>${DEVNULL?})
   [ -n "${ROVERLAY_SETUP}" ] || die "cannot locate roverlay-setup"
fi

# @private int setup_interactive__read_input (
#    message, default_value, message_suffix=":" **v0!
# )
#
#  Asks for user input and stores it in %v0.
#  Returns 0 if user input was not empty, else 1.
#
setup_interactive__read_input() {
   if [ -z "${1-}" ]; then
      die "setup_interactive__read_input(): arguments required." ${EX_ARG_ERR}
   elif [ -n "${2-}" ]; then
      # ${3-:} and not ${3:-} is not a typo
      einfo "${1} ['${2}']${3-:}"
   else
      einfo "${1}${3-:}"
   fi
   # v0= not strictly needed
   v0=; read -r v0
   [ -n "${v0}" ]
}

setup_interactive_main() {
   [ -n "${ROVERLAY_INSTALLED-}" ] || die "\$ROVERLAY_INSTALLED is not set."
   export ROVERLAY_INSTALLED

   local ROOT="${ROOT:-/}"
   local PN="roverlay"
   local ROVERLAY_CONF_ROOT="${ROOT}etc/${PN}"

   local v0
   local ask='setup_interactive__read_input'

   local data_root
   local user_conf_root
   local work_root
   local want_default_hooks=y

   local roverlay_user
   local roverlay_group
   local user_is_root

   if getent group "${PN}" 1>>${DEVNULL}; then
      roverlay_group="${PN}"
   else
      roverlay_group=
   fi

   roverlay_user="$(id -nu 2>>${DEVNULL})"
   [ -n "${roverlay_user}" ] || die "couldn\'t get user name."

   local _uid="$(id -u 2>>${DEVNULL})"
   [ -n "${_uid}" ] || die "couldn\'t get user id."


   if [ ${_uid} -eq 0 ]; then
      # ask for roverlay user
      if getent passwd "${PN}" 1>>${DEVNULL}; then
         roverlay_user="${PN}"
      fi
      if $ask \
         "Enter user/uid that will run ${PN} (user has to exist!)" \
         "${roverlay_user}"
      then
         roverlay_user="${v0}"
      fi
      case "${roverlay_user}" in
         '0'|'root')
            user_is_root=y
         ;;
         *)
            user_is_root=n
         ;;
      esac
   else
      user_is_root=n
   fi

   USER_HOME=$( getent passwd "${roverlay_user}" 2>>${DEVNULL} | \
      cut -d \: -f 6 )
   [ -n "${USER_HOME}" ] || \
      die "couldn't get home directory for user ${roverlay_user}"


   # variables depending on ROVERLAY_INSTALLED
   if [ "${ROVERLAY_INSTALLED}" = "y" ]; then
      data_root="${ROOT}usr/share/${PN}"
      if [ "${user_is_root}" = "y" ]; then
         work_root="${ROOT}var/${PN}"
         user_conf_root="${ROVERLAY_CONF_ROOT}"
         want_conf_import="disable"
      else
         work_root="${USER_HOME%/}/${PN}"
         user_conf_root="${USER_HOME%/}/${PN}/config"
         want_conf_import="symlink=dirs"
      fi

   elif [ -z "${ROVERLAY_PRJROOT-}" ]; then
      die "\$ROVERLAY_PRJROOT is not set."

   elif [ "${roverlay_user}" = "root" ] || [ "${roverlay_user}" = "0" ]; then
      die "cannot setup standalone roverlay for root."

   else
      data_root="${ROVERLAY_PRJROOT%/}/files"
      work_root="${ROVERLAY_PRJROOT%/}/workdir"
      user_conf_root="${ROVERLAY_PRJROOT%/}/config"
      want_conf_import="disable"
   fi

   : ${data_root:?}
   : ${work_root:?}
   : ${user_conf_root:?}
   : ${want_conf_import:?}

   if [ "${user_is_root}" != "y" ]; then
      if $ask \
         "Import default config (${ROVERLAY_CONF_ROOT})? (y/n/<choice>)" \
         "${want_conf_import}"
      then
         case "${v0}" in
            'y')
               want_conf_import="copy"
            ;;
            'n')
               want_conf_import="disable"
            ;;
            *)
               want_conf_import="${v0}"
            ;;
         esac
      fi
   fi

   if $ask \
      "Enable default hooks (git history and metadata cache)? (y/n)" \
      "${want_default_hooks}"
   then
      if yesno "${v0}"; then
         want_default_hooks=y
      else
         want_default_hooks=n
      fi
   fi

   if $ask \
      "Enter the directory for 'work' data (overlay, distfiles mirror)" \
      "${work_root}"
   then
      work_root="${v0}"
   fi

   local varopts=
   if yesno "${want_default_hooks}"; then
      varopts="${varopts-} --enable-default-hooks"
   else
      varopts="${varopts-} --no-default-hooks"
   fi

   set -- \
      ${ROVERLAY_SETUP?} \
         -W "${work_root}" -D "${data_root}" -C "${user_conf_root}" \
         --conf-root "${ROVERLAY_CONF_ROOT}" -I "${want_conf_import}" \
         --target-uid "${roverlay_user}" --target-gid "${roverlay_group}" \
         ${varopts-} "$@"


   if $ask "Show what would be done first? (y/n)" "n" && yesno "${v0}"; then
      autodie "$@" --pretend init
      $ask "Press Enter to continue..." || true
      autodie "$@" init

   elif $ask "Ask before each step? (y/n)" "n" && yesno "${v0}"; then
      autodie "$@" --ask init

   else
      autodie "$@" init
   fi

   einfo
   if [ ${_uid} -eq 0 ]; then
      einfo "Configuration for user '${roverlay_user}' is complete."
   else
      einfo "Configuration is complete."
   fi

   einfo "You can run '${PN} --print-config' (as user) to verify it."
   return 0
}

fi # __HAVE_SETUP_INTERACTIVE_FUNCTIONS__
